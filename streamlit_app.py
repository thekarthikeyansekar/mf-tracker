import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime

st.set_page_config(
    page_title="MF Portfolio Tracker",
    page_icon="📈",
    layout="wide",
)

# ── helpers ────────────────────────────────────────────────────────────────

def clean_num(val):
    """Strip commas/quotes and return float, or 0."""
    try:
        return float(str(val).replace(",", "").replace('"', "").strip())
    except Exception:
        return 0.0

def parse_date(val):
    """Try multiple date formats; return datetime or None."""
    s = str(val).strip()
    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y",
                "%Y-%m-%d", "%d-%B-%Y", "%d-%B-%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None

def fmt_inr(val):
    """Format number as ₹ with Indian comma style."""
    try:
        v = float(val)
        sign = "-" if v < 0 else ""
        v = abs(v)
        s = f"{v:,.0f}"
        return f"{sign}₹{s}"
    except Exception:
        return str(val)

def fmt_pct(val):
    try:
        v = float(val)
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.2f}%"
    except Exception:
        return str(val)

def load_data(uploaded_file):
    """Load and process the CSV into a clean DataFrame."""
    df = pd.read_csv(uploaded_file, skip_blank_lines=True)
    df.columns = [c.strip().replace("\n", " ") for c in df.columns]

    # Identify columns (flexible matching)
    col_map = {}
    for c in df.columns:
        cl = c.lower()
        if "vendor" in cl:               col_map["vendor"] = c
        elif "active" in cl:             col_map["active"] = c
        elif "n identifier" in cl:       col_map["n_id"] = c
        elif "invested amount" in cl:    col_map["invested"] = c
        elif "current amount" in cl:     col_map["current"] = c
        elif "xirr" in cl:               col_map["xirr"] = c
        elif cl.startswith("profit") and "%" not in cl: col_map["pnl"] = c
        elif "absolute profit" in cl:    col_map["pnl_pct"] = c
        elif "folio no" in cl:           col_map["folio"] = c
        elif "f identifier" in cl:       col_map["f_id"] = c
        elif cl == "date":               col_map["date"] = c

    df2 = pd.DataFrame()
    df2["vendor"]   = df.get(col_map.get("vendor", ""), "")
    df2["active"]   = df.get(col_map.get("active", ""), "Y")
    df2["n_id"]     = df.get(col_map.get("n_id", ""), "")
    df2["f_id"]     = df.get(col_map.get("f_id", ""), "")
    df2["folio"]    = df.get(col_map.get("folio", ""), "")
    df2["invested"] = df.get(col_map.get("invested", ""), 0).apply(clean_num)
    df2["current"]  = df.get(col_map.get("current", ""), 0).apply(clean_num)
    df2["pnl"]      = df.get(col_map.get("pnl", ""), 0).apply(clean_num)
    df2["pnl_pct"]  = df.get(col_map.get("pnl_pct", ""), 0).apply(clean_num)
    df2["xirr_raw"] = df.get(col_map.get("xirr", ""), "0%")
    df2["date_raw"] = df.get(col_map.get("date", ""), "")

    # Parse XIRR
    def parse_xirr(v):
        try:
            return float(str(v).replace("%", "").strip())
        except Exception:
            return 0.0
    df2["xirr"] = df2["xirr_raw"].apply(parse_xirr)

    # Parse date
    df2["date_parsed"] = df2["date_raw"].apply(parse_date)

    # Filter active + valid vendor
    df2["vendor"] = df2["vendor"].astype(str).str.strip()
    df2["active"] = df2["active"].astype(str).str.strip()
    df2 = df2[df2["active"].str.upper() == "Y"]
    df2 = df2[df2["vendor"].isin(["Axis", "DSP"])]
    df2 = df2[df2["n_id"].astype(str).str.strip() != ""]
    df2 = df2.reset_index(drop=True)
    return df2

def aggregate_by_fund(df, vendor, folio_key):
    """Group rows by n_id within a vendor+folio, aggregate numerics."""
    sub = df[(df["vendor"] == vendor) & (df["f_id"] == folio_key)].copy()
    if sub.empty:
        return pd.DataFrame()
    grp = sub.groupby("n_id", sort=False).agg(
        invested=("invested", "sum"),
        current=("current", "sum"),
        pnl=("pnl", "sum"),
        xirr=("xirr", "mean"),
    ).reset_index()
    grp["pnl_pct"] = (grp["pnl"] / grp["invested"].replace(0, 1)) * 100
    return grp

def build_table_html(rows_df, folio_label, folio_id, vendor_class):
    """Render one folio table as HTML string."""
    if rows_df.empty:
        return ""

    def cell_class(v):
        return "g" if float(v) >= 0 else "l"

    rows_html = ""
    for _, r in rows_df.iterrows():
        xirr_v = r["xirr"]
        pnl_v = r["pnl"]
        pnl_p = r["pnl_pct"]
        rows_html += f"""
        <tr>
          <td>{r['n_id']}</td>
          <td>{fmt_inr(r['invested'])}</td>
          <td>{fmt_inr(r['current'])}</td>
          <td class="{cell_class(xirr_v)}">{fmt_pct(xirr_v)}</td>
          <td class="{cell_class(pnl_v)}">{fmt_inr(pnl_v)}</td>
          <td class="{cell_class(pnl_p)}">{fmt_pct(pnl_p)}</td>
        </tr>"""

    # Grand total row
    t_inv = rows_df["invested"].sum()
    t_cur = rows_df["current"].sum()
    t_pnl = rows_df["pnl"].sum()
    t_pnl_p = (t_pnl / t_inv * 100) if t_inv else 0
    t_xirr = rows_df["xirr"].mean()
    rows_html += f"""
    <tr class="tr">
      <td>Grand Total</td>
      <td>{fmt_inr(t_inv)}</td>
      <td>{fmt_inr(t_cur)}</td>
      <td class="{cell_class(t_xirr)}">{fmt_pct(t_xirr)}</td>
      <td class="{cell_class(t_pnl)}">{fmt_inr(t_pnl)}</td>
      <td class="{cell_class(t_pnl_p)}">{fmt_pct(t_pnl_p)}</td>
    </tr>"""

    return f"""
    <div class="fg">
      <div class="ft">{folio_label}</div>
      <div class="tw"><table>
        <thead><tr>
          <th>Fund</th><th>Invested</th><th>Current</th>
          <th>XIRR</th><th>PnL</th><th>PnL %</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table></div>
    </div>"""

def build_vendor_section(df, vendor, vendor_label, vendor_class):
    """Build all folio tables for a vendor."""
    sub = df[df["vendor"] == vendor]
    if sub.empty:
        return ""

    folios = sub.groupby("f_id", sort=False)
    t_inv = sub["invested"].sum()
    t_cur = sub["current"].sum()

    tables_html = ""
    for f_id, grp in folios:
        agg = aggregate_by_fund(df, vendor, f_id)
        folio_display = str(grp["f_id"].iloc[0])
        tables_html += build_table_html(agg, folio_display, f_id, vendor_class)

    return f"""
    <div class="vs">
      <div class="vh">
        <span class="vp {vendor_class}">{vendor}</span>
        <span class="vt">{vendor_label} Mutual Fund</span>
        <div class="vl"></div>
        <div class="vs2">Invested <b>{fmt_inr(t_inv)}</b> &nbsp;·&nbsp; Current <b>{fmt_inr(t_cur)}</b></div>
      </div>
      {tables_html}
    </div>"""

def build_scatter_data(df):
    """Return JSON arrays for Axis and DSP scatter points."""
    axis_pts, dsp_pts = [], {}
    raw_pts = []
    for _, r in df.iterrows():
        dt = r["date_parsed"]
        if dt is None:
            continue
        iso = dt.strftime("%Y-%m-%d")
        amt = float(r["invested"])
        if amt <= 0:
            continue
        raw_pts.append({
            "iso": iso,
            "y": amt,
            "label": str(r["n_id"]),
            "vendor": str(r["vendor"]),
        })
    return json.dumps(raw_pts)

def build_insights(df):
    """Compute stat cards for scatter tab."""
    total_tx = len(df[df["date_parsed"].notna()])
    axis_tx = len(df[(df["vendor"] == "Axis") & (df["date_parsed"].notna())])
    dsp_tx  = len(df[(df["vendor"] == "DSP")  & (df["date_parsed"].notna())])

    df_d = df[df["date_parsed"].notna()].copy()
    df_d["amt"] = df_d["invested"].apply(lambda x: float(x))

    largest = df_d.loc[df_d["amt"].idxmax()] if not df_d.empty else None
    smallest = df_d.loc[df_d["amt"].idxmin()] if not df_d.empty else None

    # Most active month
    df_d["ym"] = df_d["date_parsed"].apply(lambda d: d.strftime("%b %Y"))
    busy_month = df_d.groupby("ym")["amt"].sum().idxmax() if not df_d.empty else "—"
    busy_amt = df_d.groupby("ym")["amt"].sum().max() if not df_d.empty else 0

    cards = [
        ("Total Transactions", str(total_tx), f"{axis_tx} Axis · {dsp_tx} DSP"),
        ("Largest Ticket",
         fmt_inr(largest["amt"]) if largest is not None else "—",
         f"{largest['date_parsed'].strftime('%d %b %Y')} · {str(largest['n_id'])[:30]}" if largest is not None else ""),
        ("Smallest Ticket",
         fmt_inr(smallest["amt"]) if smallest is not None else "—",
         f"{smallest['date_parsed'].strftime('%d %b %Y')} · {str(smallest['n_id'])[:30]}" if smallest is not None else ""),
        ("Most Active Month", busy_month, f"{fmt_inr(busy_amt)} invested"),
        ("Axis Transactions", str(axis_tx), "individual purchase entries"),
        ("DSP Transactions",  str(dsp_tx),  "individual purchase entries"),
    ]

    html = '<div class="ins">'
    for label, val, sub in cards:
        html += f"""
        <div class="ic">
          <div class="il">{label}</div>
          <div class="iv">{val}</div>
          <div class="is">{sub}</div>
        </div>"""
    html += "</div>"
    return html


# ── main render ────────────────────────────────────────────────────────────

def render_app(df):
    axis_inv = df[df["vendor"] == "Axis"]["invested"].sum()
    dsp_inv  = df[df["vendor"] == "DSP"]["invested"].sum()
    axis_cur = df[df["vendor"] == "Axis"]["current"].sum()
    dsp_cur  = df[df["vendor"] == "DSP"]["current"].sum()
    total_cur = axis_cur + dsp_cur
    total_pnl = df["pnl"].sum()

    holdings_html = (
        build_vendor_section(df, "Axis", "Axis", "a") +
        build_vendor_section(df, "DSP",  "DSP",  "d")
    )

    scatter_json = build_scatter_data(df)
    insights_html = build_insights(df)

    # Date range label
    dates = [d for d in df["date_parsed"] if d is not None]
    date_range = ""
    if dates:
        d0 = min(dates).strftime("%b %Y")
        d1 = max(dates).strftime("%b %Y")
        date_range = f"{d0} – {d1}"

    axis_tx = len(df[(df["vendor"] == "Axis") & (df["date_parsed"].notna())])
    dsp_tx  = len(df[(df["vendor"] == "DSP")  & (df["date_parsed"].notna())])

    pnl_class = "pos" if total_pnl >= 0 else "neg"

    HTML = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;1,9..144,300;1,9..144,400&family=DM+Mono:wght@400;500&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{{
  --bg:#0c0e14;--surface:#12141e;--surface2:#181b27;--surface3:#1f2230;
  --border:#252838;--border2:#2e3248;
  --axis-col:#f0a742;--axis-dim:rgba(240,167,66,0.12);--axis-glow:rgba(240,167,66,0.3);
  --dsp-col:#5bbcf8;--dsp-dim:rgba(91,188,248,0.12);--dsp-glow:rgba(91,188,248,0.3);
  --gain:#52d98c;--loss:#ff6b6b;
  --text1:#e8eaf6;--text2:#9499b8;--text3:#555a78;--r:14px;
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:var(--bg);color:var(--text1);font-family:'Outfit',sans-serif;min-height:100vh;overflow-x:hidden;}}
.blob{{position:fixed;border-radius:50%;filter:blur(110px);pointer-events:none;z-index:0;}}
.b1{{width:600px;height:600px;background:rgba(240,167,66,0.05);top:-180px;left:-180px;}}
.b2{{width:500px;height:500px;background:rgba(91,188,248,0.05);bottom:-150px;right:-120px;}}
.wrap{{position:relative;z-index:1;max-width:1120px;margin:0 auto;padding:32px 20px 80px;}}
/* header */
.hd{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:28px;gap:20px;flex-wrap:wrap;}}
.hd h1{{font-family:'Fraunces',serif;font-size:2.2rem;font-weight:400;letter-spacing:-.5px;line-height:1.1;}}
.hd h1 em{{font-style:italic;color:var(--axis-col);font-weight:300;}}
.hd p{{margin-top:6px;font-size:.68rem;color:var(--text3);font-family:'DM Mono',monospace;letter-spacing:.1em;text-transform:uppercase;}}
.kpis{{display:flex;gap:10px;flex-wrap:wrap;}}
.kpi{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:13px 18px;min-width:125px;position:relative;overflow:hidden;}}
.kpi::after{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:var(--ac,var(--border));opacity:.6;}}
.kpi.a{{--ac:var(--axis-col);}} .kpi.d{{--ac:var(--dsp-col);}} .kpi.g{{--ac:var(--gain);}}
.kpi-l{{font-size:.58rem;color:var(--text3);text-transform:uppercase;letter-spacing:.12em;font-family:'DM Mono',monospace;margin-bottom:5px;}}
.kpi-v{{font-family:'DM Mono',monospace;font-size:.98rem;font-weight:500;}}
.kpi-v.pos{{color:var(--gain);}} .kpi-v.neg{{color:var(--loss);}}
/* tabs */
.tabs{{display:flex;gap:3px;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:4px;width:fit-content;margin-bottom:24px;}}
.tb{{font-family:'Outfit',sans-serif;font-size:.8rem;font-weight:500;padding:8px 20px;border-radius:9px;border:none;background:transparent;color:var(--text3);cursor:pointer;transition:all .18s;display:flex;align-items:center;gap:7px;}}
.tb .d{{width:6px;height:6px;border-radius:50%;background:currentColor;opacity:.45;}}
.tb.on{{background:var(--surface3);color:var(--text1);box-shadow:0 1px 4px rgba(0,0,0,.35);}}
.tb:hover:not(.on){{color:var(--text2);}}
/* panels */
.panel{{display:none;}}
.panel.on{{display:block;animation:up .28s ease;}}
@keyframes up{{from{{opacity:0;transform:translateY(8px);}}to{{opacity:1;transform:translateY(0);}}}}
/* vendor */
.vs{{margin-bottom:36px;}}
.vh{{display:flex;align-items:center;gap:11px;margin-bottom:14px;}}
.vp{{font-size:.62rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;padding:4px 10px;border-radius:20px;font-family:'DM Mono',monospace;}}
.vp.a{{background:var(--axis-dim);color:var(--axis-col);border:1px solid rgba(240,167,66,.2);}}
.vp.d{{background:var(--dsp-dim);color:var(--dsp-col);border:1px solid rgba(91,188,248,.2);}}
.vt{{font-size:1.1rem;font-weight:600;letter-spacing:-.2px;}}
.vl{{flex:1;height:1px;background:var(--border);}}
.vs2{{font-family:'DM Mono',monospace;font-size:.72rem;color:var(--text3);white-space:nowrap;}}
.vs2 b{{color:var(--text2);font-weight:500;}}
/* folio */
.fg{{margin-bottom:18px;}}
.ft{{display:inline-flex;align-items:center;gap:6px;font-size:.64rem;color:var(--text3);text-transform:uppercase;letter-spacing:.1em;font-family:'DM Mono',monospace;margin-bottom:9px;padding:3px 10px 3px 8px;background:var(--surface2);border-radius:20px;border:1px solid var(--border);}}
.ft::before{{content:'';width:5px;height:5px;border-radius:50%;background:var(--text3);}}
/* table */
.tw{{border-radius:var(--r);border:1px solid var(--border);overflow:hidden;background:var(--surface);}}
table{{width:100%;border-collapse:collapse;}}
thead tr{{background:var(--surface2);border-bottom:1px solid var(--border);}}
th{{padding:10px 14px;font-size:.56rem;font-weight:600;text-transform:uppercase;letter-spacing:.12em;color:var(--text3);font-family:'DM Mono',monospace;text-align:right;white-space:nowrap;}}
th:first-child{{text-align:left;}}
tbody tr{{border-bottom:1px solid var(--border);transition:background .1s;}}
tbody tr:last-child{{border-bottom:none;}}
tbody tr:not(.tr):hover{{background:var(--surface2);}}
td{{padding:10px 14px;font-family:'DM Mono',monospace;font-size:.75rem;text-align:right;color:var(--text2);white-space:nowrap;}}
td:first-child{{text-align:left;font-family:'Outfit',sans-serif;font-size:.78rem;color:var(--text1);font-weight:400;max-width:250px;white-space:normal;line-height:1.45;}}
.g{{color:var(--gain)!important;}} .l{{color:var(--loss)!important;}}
.tr{{background:rgba(255,255,255,.016)!important;border-top:1px solid var(--border2)!important;}}
.tr td{{font-weight:600;color:var(--text1)!important;}}
.tr td:first-child{{font-family:'DM Mono',monospace!important;font-size:.6rem!important;letter-spacing:.1em;text-transform:uppercase;color:var(--text3)!important;}}
/* chart tab */
.ch-hd{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px;gap:16px;flex-wrap:wrap;}}
.ch-title{{font-family:'Fraunces',serif;font-size:1.4rem;font-weight:300;letter-spacing:-.3px;}}
.ch-title em{{font-style:italic;color:var(--dsp-col);}}
.ch-sub{{font-size:.68rem;color:var(--text3);font-family:'DM Mono',monospace;margin-top:5px;letter-spacing:.08em;text-transform:uppercase;}}
.leg{{display:flex;gap:18px;align-items:center;}}
.li{{display:flex;align-items:center;gap:8px;font-size:.78rem;color:var(--text2);}}
.ld{{width:10px;height:10px;border-radius:50%;}}
.lv{{font-family:'DM Mono',monospace;font-weight:500;}}
.cc{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:24px;position:relative;}}
.cc::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent 5%,var(--axis-col) 30%,var(--dsp-col) 70%,transparent 95%);opacity:.35;border-radius:var(--r) var(--r) 0 0;}}
.cw{{position:relative;height:400px;}}
.ins{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:16px;}}
.ic{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px;}}
.il{{font-size:.58rem;color:var(--text3);text-transform:uppercase;letter-spacing:.1em;font-family:'DM Mono',monospace;margin-bottom:5px;}}
.iv{{font-size:1rem;font-weight:600;font-family:'DM Mono',monospace;}}
.is{{font-size:.7rem;color:var(--text3);margin-top:3px;}}
</style>
</head>
<body>
<div class="blob b1"></div>
<div class="blob b2"></div>
<div class="wrap">

  <div class="hd">
    <div>
      <h1>Portfolio <em>Tracker</em></h1>
      <p>Active Holdings &middot; Axis &amp; DSP &middot; {date_range}</p>
    </div>
    <div class="kpis">
      <div class="kpi a"><div class="kpi-l">Axis Invested</div><div class="kpi-v">{fmt_inr(axis_inv)}</div></div>
      <div class="kpi d"><div class="kpi-l">DSP Invested</div><div class="kpi-v">{fmt_inr(dsp_inv)}</div></div>
      <div class="kpi g"><div class="kpi-l">Total Current</div><div class="kpi-v">{fmt_inr(total_cur)}</div></div>
      <div class="kpi g"><div class="kpi-l">Overall PnL</div><div class="kpi-v {pnl_class}">{fmt_inr(total_pnl)}</div></div>
    </div>
  </div>

  <div class="tabs">
    <button class="tb on" onclick="sw('h',this)"><span class="d"></span> Holdings</button>
    <button class="tb" onclick="sw('t',this)"><span class="d"></span> Investment Journey</button>
  </div>

  <div class="panel on" id="p-h">
    {holdings_html}
  </div>

  <div class="panel" id="p-t">
    <div class="ch-hd">
      <div>
        <div class="ch-title">Investment <em>Scatter</em></div>
        <div class="ch-sub">Each dot = one transaction &middot; size &prop; amount &middot; {date_range}</div>
      </div>
      <div class="leg">
        <div class="li">
          <div class="ld" style="background:var(--axis-col);box-shadow:0 0 8px var(--axis-glow);"></div>
          <span>Axis</span>
          <span class="lv" style="color:var(--axis-col);">{axis_tx} transactions</span>
        </div>
        <div class="li">
          <div class="ld" style="background:var(--dsp-col);box-shadow:0 0 8px var(--dsp-glow);"></div>
          <span>DSP</span>
          <span class="lv" style="color:var(--dsp-col);">{dsp_tx} transactions</span>
        </div>
      </div>
    </div>
    <div class="cc"><div class="cw"><canvas id="chart"></canvas></div></div>
    {insights_html}
  </div>

</div>

<script>
function sw(id,btn){{
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));
  document.querySelectorAll('.tb').forEach(b=>b.classList.remove('on'));
  document.getElementById('p-'+id).classList.add('on');
  btn.classList.add('on');
  if(id==='t') setTimeout(drawChart,80);
}}

const RAW = {scatter_json};

function ts(iso){{ return new Date(iso).getTime(); }}
function radius(amt){{ return Math.max(5,Math.min(26,Math.sqrt(amt/500)*5)); }}
function fmtDate(ms){{ return new Date(ms).toLocaleDateString('en-IN',{{day:'numeric',month:'short',year:'numeric'}}); }}
function fmtTick(ms){{ const d=new Date(ms); return d.toLocaleDateString('en-GB',{{month:'short',year:'2-digit'}}); }}
function buildTicks(mn,mx,n){{ const s=(mx-mn)/(n-1); return Array.from({{length:n}},(_,i)=>mn+i*s); }}

let drawn=false;
function drawChart(){{
  if(drawn) return; drawn=true;
  const axPts=RAW.filter(d=>d.vendor==='Axis').map(d=>({{x:ts(d.iso),y:d.y,iso:d.iso,label:d.label,r:radius(d.y)}}));
  const dsPts=RAW.filter(d=>d.vendor==='DSP').map(d=>({{x:ts(d.iso),y:d.y,iso:d.iso,label:d.label,r:radius(d.y)}}));
  const allX=RAW.map(d=>ts(d.iso));
  const minX=Math.min(...allX)-30*24*3600000;
  const maxX=Math.max(...allX)+30*24*3600000;
  const ctx=document.getElementById('chart').getContext('2d');
  new Chart(ctx,{{
    type:'bubble',
    data:{{datasets:[
      {{label:'Axis',data:axPts,backgroundColor:'rgba(240,167,66,0.55)',borderColor:'rgba(240,167,66,0.88)',borderWidth:1.5,hoverBackgroundColor:'rgba(240,167,66,0.85)',hoverBorderColor:'#f0a742',hoverBorderWidth:2}},
      {{label:'DSP', data:dsPts,backgroundColor:'rgba(91,188,248,0.5)', borderColor:'rgba(91,188,248,0.88)',borderWidth:1.5,hoverBackgroundColor:'rgba(91,188,248,0.82)',hoverBorderColor:'#5bbcf8',hoverBorderWidth:2}}
    ]}},
    options:{{
      responsive:true,maintainAspectRatio:false,
      plugins:{{
        legend:{{display:false}},
        tooltip:{{
          backgroundColor:'#1a1d27',borderColor:'#2e3248',borderWidth:1,
          titleColor:'#9499b8',bodyColor:'#e8eaf6',padding:14,
          titleFont:{{family:'DM Mono',size:11}},bodyFont:{{family:'DM Mono',size:12}},
          callbacks:{{
            title:items=>fmtDate(items[0].raw.x),
            label:item=>['  '+item.dataset.label,'  ₹'+item.raw.y.toLocaleString('en-IN'),'  '+item.raw.label.replace(/_/g,' ')]
          }}
        }}
      }},
      scales:{{
        x:{{type:'linear',min:minX,max:maxX,
          grid:{{color:'rgba(255,255,255,0.04)',drawTicks:false}},
          ticks:{{color:'#555a78',font:{{family:'DM Mono',size:10}},maxRotation:0,maxTicksLimit:12,callback:v=>fmtTick(v)}},
          afterBuildTicks(axis){{axis.ticks=buildTicks(Math.min(...allX),Math.max(...allX),12).map(v=>({{value:v}}));}},
          border:{{color:'#252838'}}
        }},
        y:{{
          title:{{display:true,text:'Amount Invested (₹)',color:'#555a78',font:{{family:'DM Mono',size:10}}}},
          grid:{{color:'rgba(255,255,255,0.04)',drawTicks:false}},
          ticks:{{color:'#555a78',font:{{family:'DM Mono',size:10}},callback:v=>v>=1000?'₹'+(v/1000).toFixed(0)+'k':'₹'+v,maxTicksLimit:8}},
          border:{{color:'#252838'}}
        }}
      }}
    }}
  }});
}}
</script>
</body>
</html>
"""
    st.components.v1.html(HTML, height=1800, scrolling=True)


# ── page ───────────────────────────────────────────────────────────────────

# Hide Streamlit chrome and make background dark
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0c0e14; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #12141e; border-right: 1px solid #252838; }
[data-testid="stFileUploader"] {
    background: #12141e; border: 1px dashed #2e3248;
    border-radius: 14px; padding: 20px;
}
[data-testid="stFileUploader"] * { color: #9499b8 !important; }
.stButton>button {
    background: #1f2230; color: #e8eaf6;
    border: 1px solid #252838; border-radius: 10px;
}
div[data-testid="stMarkdownContainer"] p { color: #9499b8; }
</style>
""", unsafe_allow_html=True)

# Sidebar uploader
with st.sidebar:
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:.7rem;color:#555a78;
         text-transform:uppercase;letter-spacing:.1em;margin-bottom:16px;">
        MF Portfolio Tracker
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload your CSV",
        type=["csv"],
        help="Upload the Asset_Tracker CSV exported from your spreadsheet",
    )

    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:.65rem;color:#3a3f58;
         margin-top:24px;line-height:1.8;">
        Expected columns:<br>
        Vendor · Active · N Identifier<br>
        F Identifier · Date<br>
        Invested Amount · Current Amount<br>
        Profit · Absolute Profit % · XIRR
    </div>
    """, unsafe_allow_html=True)

if uploaded is None:
    # Landing state
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
         height:80vh;font-family:'Outfit',sans-serif;text-align:center;">
      <div style="font-family:Georgia,serif;font-size:3rem;font-weight:400;color:#e8eaf6;letter-spacing:-.5px;">
        Portfolio <em style="color:#f0a742;font-style:italic;">Tracker</em>
      </div>
      <div style="font-size:.85rem;color:#555a78;font-family:'DM Mono',monospace;
           text-transform:uppercase;letter-spacing:.12em;margin-top:12px;">
        Upload your CSV in the sidebar to begin
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    try:
        df = load_data(uploaded)
        if df.empty:
            st.error("No active Axis/DSP holdings found. Check your CSV format.")
        else:
            render_app(df)
    except Exception as e:
        st.error(f"Could not parse CSV: {e}")
        st.exception(e)
