import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Portfolio Tracker",
    page_icon="📈",
    layout="wide",
)

# ── helpers ────────────────────────────────────────────────────────────────

def clean_num(val):
    try:
        return float(str(val).replace(",", "").replace('"', "").strip())
    except Exception:
        return 0.0

def parse_date(val):
    s = str(val).strip()
    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y",
                "%Y-%m-%d", "%d-%B-%Y", "%d-%B-%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None

def fmt_inr(val):
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

# ── MF data loading ────────────────────────────────────────────────────────

def load_mf_data(xl, sheet_name="MF Tracker Data"):
    df = xl.parse(sheet_name, skip_blank_lines=True)
    df.columns = [c.strip().replace("\n", " ") for c in df.columns]

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

    def parse_xirr(v):
        try:
            return float(str(v).replace("%", "").strip())
        except Exception:
            return 0.0

    df2["xirr"] = df2["xirr_raw"].apply(parse_xirr)
    df2["date_parsed"] = df2["date_raw"].apply(parse_date)
    df2["vendor"] = df2["vendor"].astype(str).str.strip()
    df2["active"] = df2["active"].astype(str).str.strip()
    df2 = df2[df2["active"].str.upper() == "Y"]
    df2 = df2[df2["vendor"].isin(["Axis", "DSP"])]
    df2 = df2[df2["n_id"].astype(str).str.strip() != ""]
    df2 = df2.reset_index(drop=True)
    return df2

# ── NPS data loading ───────────────────────────────────────────────────────

def load_nps_data(xl, sheet_name="NPS Tracker Data"):
    df = xl.parse(sheet_name, skip_blank_lines=True)
    df.columns = [c.strip() for c in df.columns]

    def parse_col(df, names):
        for n in names:
            if n in df.columns:
                return n
        for c in df.columns:
            for n in names:
                if n.lower() in c.lower():
                    return c
        return None

    year_col   = parse_col(df, ["Year"])
    cat_col    = parse_col(df, ["Category"])
    fund_col   = parse_col(df, ["Fund Name"])
    date_col   = parse_col(df, ["Date"])
    part_col   = parse_col(df, ["Particulars"])
    amt_col    = parse_col(df, ["Amount"])
    nav_col    = parse_col(df, ["NAV"])
    units_col  = parse_col(df, ["Units"])

    df2 = pd.DataFrame()
    df2["year"]       = df[year_col].astype(str) if year_col else ""
    df2["category"]   = df[cat_col].astype(str).str.strip() if cat_col else ""
    df2["fund_name"]  = df[fund_col].astype(str).str.strip() if fund_col else ""
    df2["particulars"]= df[part_col].astype(str).str.strip() if part_col else ""
    df2["amount"]     = df[amt_col].apply(clean_num) if amt_col else 0.0
    df2["nav"]        = df[nav_col].apply(clean_num) if nav_col else 0.0
    df2["units"]      = df[units_col].apply(clean_num) if units_col else 0.0
    df2["date_parsed"] = df[date_col].apply(parse_date) if date_col else None

    df2 = df2[df2["date_parsed"].notna()]
    df2 = df2[df2["amount"] > 0]
    df2 = df2.reset_index(drop=True)
    return df2

# ── MF rendering ───────────────────────────────────────────────────────────

def aggregate_by_fund(df, vendor, folio_key):
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
    total_tx = len(df[df["date_parsed"].notna()])
    axis_tx = len(df[(df["vendor"] == "Axis") & (df["date_parsed"].notna())])
    dsp_tx  = len(df[(df["vendor"] == "DSP")  & (df["date_parsed"].notna())])

    df_d = df[df["date_parsed"].notna()].copy()
    df_d["amt"] = df_d["invested"].apply(lambda x: float(x))

    largest = df_d.loc[df_d["amt"].idxmax()] if not df_d.empty else None
    smallest = df_d.loc[df_d["amt"].idxmin()] if not df_d.empty else None

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


# ── MF tab renderer ────────────────────────────────────────────────────────

def render_mf_tab(df):
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
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;1,9..144,300;1,9..144,400&family=DM+Mono:wght@400;500&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{{
  --bg:#1c1c1c;--surface:#262626;--surface2:#2f2f2f;--surface3:#383838;
  --border:#404040;--border2:#505050;
  --axis-col:#c9933a;--axis-dim:rgba(201,147,58,0.14);--axis-glow:rgba(201,147,58,0.3);
  --dsp-col:#5aaee0;--dsp-dim:rgba(90,174,224,0.14);--dsp-glow:rgba(90,174,224,0.3);
  --gain:#4ec98a;--loss:#e05a5a;
  --text1:#ffffff;--text2:#cccccc;--text3:#888888;--r:14px;
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:var(--bg);color:var(--text1);font-family:'Outfit',sans-serif;}}
.blob{{position:fixed;border-radius:50%;filter:blur(110px);pointer-events:none;z-index:0;}}
.b1{{width:600px;height:600px;background:rgba(201,147,58,0.06);top:-180px;left:-180px;}}
.b2{{width:500px;height:500px;background:rgba(90,174,224,0.06);bottom:-150px;right:-120px;}}
.wrap{{position:relative;z-index:1;max-width:1120px;margin:0 auto;padding:28px 20px 60px;}}
.hd{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:28px;gap:20px;flex-wrap:wrap;}}
.hd h1{{font-family:'Fraunces',serif;font-size:2rem;font-weight:400;letter-spacing:-.5px;line-height:1.1;}}
.hd h1 em{{font-style:italic;color:var(--axis-col);font-weight:300;}}
.hd p{{margin-top:6px;font-size:.68rem;color:var(--text3);font-family:'DM Mono',monospace;letter-spacing:.1em;text-transform:uppercase;}}
.kpis{{display:flex;gap:10px;flex-wrap:wrap;}}
.kpi{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:13px 18px;min-width:125px;position:relative;overflow:hidden;}}
.kpi::after{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:var(--ac,var(--border));opacity:.6;}}
.kpi.a{{--ac:var(--axis-col);}} .kpi.d{{--ac:var(--dsp-col);}} .kpi.g{{--ac:var(--gain);}}
.kpi-l{{font-size:.58rem;color:var(--text3);text-transform:uppercase;letter-spacing:.12em;font-family:'DM Mono',monospace;margin-bottom:5px;}}
.kpi-v{{font-family:'DM Mono',monospace;font-size:.98rem;font-weight:500;}}
.kpi-v.pos{{color:var(--gain);}} .kpi-v.neg{{color:var(--loss);}}
.tabs{{display:flex;gap:3px;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:4px;width:fit-content;margin-bottom:24px;}}
.tb{{font-family:'Outfit',sans-serif;font-size:.8rem;font-weight:500;padding:8px 20px;border-radius:9px;border:none;background:transparent;color:var(--text3);cursor:pointer;transition:all .18s;display:flex;align-items:center;gap:7px;}}
.tb .d{{width:6px;height:6px;border-radius:50%;background:currentColor;opacity:.45;}}
.tb.on{{background:var(--surface3);color:var(--text1);box-shadow:0 1px 4px rgba(0,0,0,.35);}}
.tb:hover:not(.on){{color:var(--text2);}}
.panel{{display:none;}} .panel.on{{display:block;animation:up .28s ease;}}
@keyframes up{{from{{opacity:0;transform:translateY(8px);}}to{{opacity:1;transform:translateY(0);}}}}
.vs{{margin-bottom:36px;}}
.vh{{display:flex;align-items:center;gap:11px;margin-bottom:14px;}}
.vp{{font-size:.62rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;padding:4px 10px;border-radius:20px;font-family:'DM Mono',monospace;}}
.vp.a{{background:var(--axis-dim);color:var(--axis-col);border:1px solid rgba(201,147,58,.25);}}
.vp.d{{background:var(--dsp-dim);color:var(--dsp-col);border:1px solid rgba(90,174,224,.25);}}
.vt{{font-size:1.1rem;font-weight:600;letter-spacing:-.2px;}}
.vl{{flex:1;height:1px;background:var(--border);}}
.vs2{{font-family:'DM Mono',monospace;font-size:.72rem;color:var(--text3);white-space:nowrap;}}
.vs2 b{{color:var(--text2);font-weight:500;}}
.fg{{margin-bottom:18px;}}
.ft{{display:inline-flex;align-items:center;gap:6px;font-size:.64rem;color:var(--text3);text-transform:uppercase;letter-spacing:.1em;font-family:'DM Mono',monospace;margin-bottom:9px;padding:3px 10px 3px 8px;background:var(--surface2);border-radius:20px;border:1px solid var(--border);}}
.ft::before{{content:'';width:5px;height:5px;border-radius:50%;background:var(--text3);}}
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
<div class="blob b1"></div><div class="blob b2"></div>
<div class="wrap">
  <div class="hd">
    <div>
      <h1>Mutual Fund <em>Holdings</em></h1>
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
  <div class="panel on" id="p-h">{holdings_html}</div>
  <div class="panel" id="p-t">
    <div class="ch-hd">
      <div>
        <div class="ch-title">Investment <em>Scatter</em></div>
        <div class="ch-sub">Each dot = one transaction &middot; size &prop; amount &middot; {date_range}</div>
      </div>
      <div class="leg">
        <div class="li"><div class="ld" style="background:var(--axis-col);box-shadow:0 0 8px var(--axis-glow);"></div><span>Axis</span><span class="lv" style="color:var(--axis-col);">{axis_tx} transactions</span></div>
        <div class="li"><div class="ld" style="background:var(--dsp-col);box-shadow:0 0 8px var(--dsp-glow);"></div><span>DSP</span><span class="lv" style="color:var(--dsp-col);">{dsp_tx} transactions</span></div>
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
const RAW={scatter_json};
function ts(iso){{return new Date(iso).getTime();}}
function radius(amt){{return Math.max(5,Math.min(26,Math.sqrt(amt/500)*5));}}
function fmtDate(ms){{return new Date(ms).toLocaleDateString('en-IN',{{day:'numeric',month:'short',year:'numeric'}});}}
function buildTicks(mn,mx,n){{const s=(mx-mn)/(n-1);return Array.from({{length:n}},(_,i)=>mn+i*s);}}
let drawn=false;
function drawChart(){{
  if(drawn)return;drawn=true;
  const axPts=RAW.filter(d=>d.vendor==='Axis').map(d=>({{x:ts(d.iso),y:d.y,iso:d.iso,label:d.label,r:radius(d.y)}}));
  const dsPts=RAW.filter(d=>d.vendor==='DSP').map(d=>({{x:ts(d.iso),y:d.y,iso:d.iso,label:d.label,r:radius(d.y)}}));
  const allX=RAW.map(d=>ts(d.iso));
  const minX=Math.min(...allX)-30*24*3600000;
  const maxX=Math.max(...allX)+30*24*3600000;
  const ctx=document.getElementById('chart').getContext('2d');
  new Chart(ctx,{{type:'bubble',data:{{datasets:[
    {{label:'Axis',data:axPts,backgroundColor:'rgba(240,167,66,0.55)',borderColor:'rgba(240,167,66,0.88)',borderWidth:1.5,hoverBackgroundColor:'rgba(240,167,66,0.85)',hoverBorderColor:'#f0a742',hoverBorderWidth:2}},
    {{label:'DSP',data:dsPts,backgroundColor:'rgba(91,188,248,0.5)',borderColor:'rgba(91,188,248,0.88)',borderWidth:1.5,hoverBackgroundColor:'rgba(91,188,248,0.82)',hoverBorderColor:'#5bbcf8',hoverBorderWidth:2}}
  ]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'#2a2a2a',borderColor:'#484848',borderWidth:1,titleColor:'#9499b8',bodyColor:'#e8eaf6',padding:14,titleFont:{{family:'DM Mono',size:11}},bodyFont:{{family:'DM Mono',size:12}},callbacks:{{title:items=>fmtDate(items[0].raw.x),label:item=>['  '+item.dataset.label,'  ₹'+item.raw.y.toLocaleString('en-IN'),'  '+item.raw.label.replace(/_/g,' ')]}}}}}},scales:{{x:{{type:'linear',min:minX,max:maxX,grid:{{color:'rgba(255,255,255,0.06)',drawTicks:false}},ticks:{{color:'#555a78',font:{{family:'DM Mono',size:10}},maxRotation:0,maxTicksLimit:12,callback:v=>new Date(v).toLocaleDateString('en-GB',{{month:'short',year:'2-digit'}})}},afterBuildTicks(axis){{axis.ticks=buildTicks(Math.min(...allX),Math.max(...allX),12).map(v=>({{value:v}}));}},border:{{color:'#404040'}}}},y:{{title:{{display:true,text:'Amount Invested (₹)',color:'#555a78',font:{{family:'DM Mono',size:10}}}},grid:{{color:'rgba(255,255,255,0.06)',drawTicks:false}},ticks:{{color:'#555a78',font:{{family:'DM Mono',size:10}},callback:v=>v>=1000?'₹'+(v/1000).toFixed(0)+'k':'₹'+v,maxTicksLimit:8}},border:{{color:'#404040'}}}}}}}}}}));
}}
</script>
</body></html>"""

    st.components.v1.html(HTML, height=1800, scrolling=True)


# ── NPS tab renderer ───────────────────────────────────────────────────────

def render_nps_tab(df):
    total_invested = df["amount"].sum()
    total_units    = df["units"].sum()
    latest_nav     = df.loc[df["date_parsed"].idxmax(), "nav"] if not df.empty else 0
    current_val    = total_units * latest_nav

    # ── Summary KPIs ──────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Invested", fmt_inr(total_invested))
    with col2:
        st.metric("Total Units", f"{total_units:,.2f}")
    with col3:
        st.metric("Latest NAV", f"₹{latest_nav:.2f}")
    with col4:
        gain = current_val - total_invested
        st.metric("Est. Current Value", fmt_inr(current_val), delta=fmt_inr(gain))

    st.divider()

    # ── Fund filter ───────────────────────────────────────────────────────
    funds = sorted(df["fund_name"].unique())
    categories = sorted(df["category"].unique())

    c1, c2 = st.columns([2, 1])
    with c1:
        sel_funds = st.multiselect("Filter by Fund", funds, default=funds, key="nps_fund_filter")
    with c2:
        sel_cats = st.multiselect("Category", categories, default=categories, key="nps_cat_filter")

    dff = df[df["fund_name"].isin(sel_funds) & df["category"].isin(sel_cats)].copy()

    if dff.empty:
        st.warning("No data matches the selected filters.")
        return

    dff = dff.sort_values("date_parsed")

    # ── Chart 1: NAV Timeline + Units Bar (dual axis) ─────────────────────
    st.subheader("📈 NAV Timeline & Units Invested")

    # Aggregate by date for NAV line; keep per-fund resolution for scatter
    daily = dff.groupby("date_parsed").agg(
        amount=("amount", "sum"),
        units=("units", "sum"),
        nav=("nav", "mean"),
    ).reset_index()

    colors_map = {
        "Equity":   "#c9933a",
        "Debt":     "#5aaee0",
        "Balanced": "#9b7fd4",
        "Corporate Bond": "#4ec98a",
        "Govt Sec": "#e05a5a",
    }

    fig1 = make_subplots(
        specs=[[{"secondary_y": True}]],
    )

    # NAV line per fund
    for fund in sel_funds:
        fd = dff[dff["fund_name"] == fund].sort_values("date_parsed")
        if fd.empty:
            continue
        cat = fd["category"].iloc[0]
        col = colors_map.get(cat, "#aaaaaa")
        short_name = fund.split("SCHEME")[0].strip()[-40:] if "SCHEME" in fund else fund[:40]
        fig1.add_trace(
            go.Scatter(
                x=fd["date_parsed"], y=fd["nav"],
                mode="lines+markers",
                name=f"NAV – {short_name}",
                line=dict(color=col, width=2),
                marker=dict(size=5, color=col),
                hovertemplate="<b>%{text}</b><br>Date: %{x|%d %b %Y}<br>NAV: ₹%{y:.2f}<extra></extra>",
                text=[short_name]*len(fd),
            ),
            secondary_y=False,
        )

    # Units bar (aggregated daily)
    fig1.add_trace(
        go.Bar(
            x=daily["date_parsed"], y=daily["units"],
            name="Units Acquired",
            marker_color="rgba(255,255,255,0.08)",
            marker_line_color="rgba(255,255,255,0.18)",
            marker_line_width=1,
            hovertemplate="Date: %{x|%d %b %Y}<br>Units: %{y:.2f}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig1.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1c1c1c",
        plot_bgcolor="#262626",
        font=dict(family="DM Mono, monospace", size=11, color="#cccccc"),
        legend=dict(
            bgcolor="rgba(38,38,38,0.9)",
            bordercolor="#404040",
            borderwidth=1,
            font=dict(size=10),
        ),
        margin=dict(l=60, r=60, t=30, b=50),
        height=480,
        hovermode="x unified",
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            showgrid=True,
            zeroline=False,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            title="NAV (₹)",
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
            tickprefix="₹",
            tickfont=dict(size=10),
        ),
        yaxis2=dict(
            title="Units Acquired",
            overlaying="y",
            side="right",
            gridcolor="rgba(255,255,255,0.03)",
            zeroline=False,
            tickfont=dict(size=10),
        ),
        barmode="overlay",
    )
    st.plotly_chart(fig1, use_container_width=True)

    # ── Chart 2: Cumulative Investment + Monthly Bar ───────────────────────
    st.subheader("💰 Investment Timeline")

    # Monthly aggregation
    dff["ym"] = dff["date_parsed"].apply(lambda d: d.replace(day=1))
    monthly = dff.groupby("ym").agg(amount=("amount", "sum"), units=("units", "sum")).reset_index()
    monthly = monthly.sort_values("ym")
    monthly["cumulative"] = monthly["amount"].cumsum()

    fig2 = make_subplots(specs=[[{"secondary_y": True}]])

    # Monthly bar
    fig2.add_trace(
        go.Bar(
            x=monthly["ym"], y=monthly["amount"],
            name="Monthly Investment",
            marker_color="rgba(201,147,58,0.55)",
            marker_line_color="rgba(201,147,58,0.85)",
            marker_line_width=1,
            hovertemplate="Month: %{x|%b %Y}<br>Invested: ₹%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Cumulative line
    fig2.add_trace(
        go.Scatter(
            x=monthly["ym"], y=monthly["cumulative"],
            mode="lines",
            name="Cumulative Invested",
            line=dict(color="#4ec98a", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(78,201,138,0.07)",
            hovertemplate="Month: %{x|%b %Y}<br>Cumulative: ₹%{y:,.0f}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig2.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1c1c1c",
        plot_bgcolor="#262626",
        font=dict(family="DM Mono, monospace", size=11, color="#cccccc"),
        legend=dict(bgcolor="rgba(38,38,38,0.9)", bordercolor="#404040", borderwidth=1, font=dict(size=10)),
        margin=dict(l=60, r=60, t=30, b=50),
        height=400,
        hovermode="x unified",
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False, tickfont=dict(size=10)),
        yaxis=dict(title="Monthly Amount (₹)", gridcolor="rgba(255,255,255,0.06)", zeroline=False, tickprefix="₹", tickfont=dict(size=10)),
        yaxis2=dict(title="Cumulative (₹)", overlaying="y", side="right", zeroline=False, tickprefix="₹", tickfont=dict(size=10)),
        barmode="overlay",
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Chart 3: Category Breakdown ───────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🥧 By Category")
        cat_grp = dff.groupby("category")["amount"].sum().reset_index()
        cat_colors = [colors_map.get(c, "#888888") for c in cat_grp["category"]]
        fig3 = go.Figure(go.Pie(
            labels=cat_grp["category"],
            values=cat_grp["amount"],
            marker=dict(colors=cat_colors, line=dict(color="#1c1c1c", width=2)),
            textfont=dict(family="DM Mono, monospace", size=11),
            hole=0.42,
            hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>",
        ))
        fig3.update_layout(
            paper_bgcolor="#1c1c1c", plot_bgcolor="#1c1c1c",
            font=dict(family="DM Mono, monospace", size=11, color="#cccccc"),
            margin=dict(l=10, r=10, t=20, b=10), height=320,
            legend=dict(bgcolor="rgba(38,38,38,0.9)", bordercolor="#404040", borderwidth=1, font=dict(size=10)),
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col_b:
        st.subheader("📊 Yearly Investment")
        yr_grp = dff.groupby("year")["amount"].sum().reset_index().sort_values("year")
        fig4 = go.Figure(go.Bar(
            x=yr_grp["year"], y=yr_grp["amount"],
            marker_color="#5aaee0",
            marker_line_color="rgba(90,174,224,0.5)",
            marker_line_width=1,
            hovertemplate="Year: %{x}<br>Invested: ₹%{y:,.0f}<extra></extra>",
            text=[fmt_inr(v) for v in yr_grp["amount"]],
            textposition="outside",
            textfont=dict(size=10, color="#cccccc"),
        ))
        fig4.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1c1c1c", plot_bgcolor="#262626",
            font=dict(family="DM Mono, monospace", size=11, color="#cccccc"),
            margin=dict(l=40, r=20, t=20, b=40), height=320,
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False, tickprefix="₹"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False),
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ── Raw data table ─────────────────────────────────────────────────────
    with st.expander("📋 Raw Transaction Data"):
        show = dff[["date_parsed", "year", "category", "fund_name", "particulars", "amount", "nav", "units"]].copy()
        show["date_parsed"] = show["date_parsed"].apply(lambda d: d.strftime("%d %b %Y"))
        show["amount"] = show["amount"].apply(fmt_inr)
        show.columns = ["Date", "Year", "Category", "Fund", "Particulars", "Amount", "NAV", "Units"]
        st.dataframe(show, use_container_width=True)


# ── Streamlit dark chrome ──────────────────────────────────────────────────

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #1c1c1c; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #222222; border-right: 1px solid #3a3a3a; }
[data-testid="stFileUploader"] { background: #262626; border: 1px dashed #505050; border-radius: 14px; padding: 20px; }
[data-testid="stFileUploader"] * { color: #cccccc !important; }
.stButton>button { background: #303030; color: #ffffff; border: 1px solid #404040; border-radius: 10px; }
div[data-testid="stMarkdownContainer"] p { color: #cccccc; }
[data-testid="stMetric"] { background: #262626; border: 1px solid #404040; border-radius: 12px; padding: 14px 18px; }
[data-testid="stMetricLabel"] { color: #888888 !important; font-size: .7rem !important; }
[data-testid="stMetricValue"] { color: #ffffff !important; font-family: 'DM Mono', monospace !important; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:.7rem;color:#888888;
         text-transform:uppercase;letter-spacing:.1em;margin-bottom:16px;">
        Portfolio Tracker
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload your XLSX",
        type=["xlsx"],
        help="Upload the Asset_Tracker XLSX file",
    )

    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:.65rem;color:#666666;
         margin-top:24px;line-height:1.8;">
        Expected sheets:<br>
        · MF Tracker Data<br>
        · NPS Tracker Data<br><br>
        MF columns:<br>
        Vendor · Active · N Identifier<br>
        F Identifier · Date<br>
        Invested Amount · Current Amount<br>
        Profit · Absolute Profit % · XIRR<br><br>
        NPS columns:<br>
        Year · Category · Fund Name<br>
        Date · Particulars<br>
        Amount · NAV · Units
    </div>
    """, unsafe_allow_html=True)


# ── Main ───────────────────────────────────────────────────────────────────

if uploaded is None:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
         height:80vh;font-family:'Outfit',sans-serif;text-align:center;">
      <div style="font-family:Georgia,serif;font-size:3rem;font-weight:400;color:#ffffff;letter-spacing:-.5px;">
        Portfolio <em style="color:#c9933a;font-style:italic;">Tracker</em>
      </div>
      <div style="font-size:.85rem;color:#888888;font-family:'DM Mono',monospace;
           text-transform:uppercase;letter-spacing:.12em;margin-top:12px;">
        Upload your XLSX in the sidebar to begin
      </div>
      <div style="font-size:.75rem;color:#555555;font-family:'DM Mono',monospace;margin-top:8px;">
        Supports: MF Tracker Data · NPS Tracker Data
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    try:
        xl = pd.ExcelFile(uploaded)
        sheet_names = xl.sheet_names

        has_mf  = "MF Tracker Data"  in sheet_names
        has_nps = "NPS Tracker Data" in sheet_names

        if not has_mf and not has_nps:
            st.error("Neither 'MF Tracker Data' nor 'NPS Tracker Data' sheets found in the uploaded file.")
        else:
            # Build tab list dynamically
            tab_labels = []
            if has_mf:
                tab_labels.append("📊 Mutual Funds")
            if has_nps:
                tab_labels.append("🏛️ NPS")

            tabs = st.tabs(tab_labels)
            tab_idx = 0

            if has_mf:
                with tabs[tab_idx]:
                    try:
                        mf_df = load_mf_data(xl)
                        if mf_df.empty:
                            st.warning("No active Axis/DSP holdings found in 'MF Tracker Data'. Check vendor names and Active column.")
                        else:
                            render_mf_tab(mf_df)
                    except Exception as e:
                        st.error(f"Error loading MF data: {e}")
                        st.exception(e)
                tab_idx += 1

            if has_nps:
                with tabs[tab_idx]:
                    try:
                        nps_df = load_nps_data(xl)
                        if nps_df.empty:
                            st.warning("No valid rows found in 'NPS Tracker Data'. Check date format and Amount column.")
                        else:
                            render_nps_tab(nps_df)
                    except Exception as e:
                        st.error(f"Error loading NPS data: {e}")
                        st.exception(e)

    except Exception as e:
        st.error(f"Could not open XLSX: {e}")
        st.exception(e)
