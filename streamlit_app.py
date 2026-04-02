import streamlit as st
import pandas as pd
import json
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

SCHEMES = {
    "E": "SM008001",
    "C": "SM008002",
    "G": "SM008003"
}



st.set_page_config(
    page_title="Portfolio Tracker",
    page_icon="📈",
    layout="wide",
)


def fetch_latest_nav(scheme_code):
    url = f"https://npsnav.in/api/{scheme_code}"
    res = requests.get(url)
    data = res.json()

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df["nav"] = df["nav"].astype(float)

    return df.sort_values("date").iloc[-1]["nav"]

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
        return f"{sign}₹{v:,.0f}"
    except Exception:
        return str(val)

def fmt_pct(val):
    try:
        v = float(val)
        return f"{'+'if v>=0 else ''}{v:.2f}%"
    except Exception:
        return str(val)


# ══════════════════════════════════════════════════════════════════════════
#  MF TAB
# ══════════════════════════════════════════════════════════════════════════

def load_mf_data(uploaded_file):
    df = pd.read_csv(uploaded_file, skip_blank_lines=True)
    df.columns = [c.strip().replace("\n", " ") for c in df.columns]

    col_map = {}
    for c in df.columns:
        cl = c.lower()
        if "vendor" in cl:                           col_map["vendor"] = c
        elif "active" in cl:                         col_map["active"] = c
        elif "n identifier" in cl:                   col_map["n_id"] = c
        elif "invested amount" in cl:                col_map["invested"] = c
        elif "current amount" in cl:                 col_map["current"] = c
        elif "xirr" in cl:                           col_map["xirr"] = c
        elif cl.startswith("profit") and "%" not in cl: col_map["pnl"] = c
        elif "absolute profit" in cl:                col_map["pnl_pct"] = c
        elif "folio no" in cl:                       col_map["folio"] = c
        elif "f identifier" in cl:                   col_map["f_id"] = c
        elif cl == "date":                           col_map["date"] = c

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

    df2["xirr"] = df2["xirr_raw"].apply(
        lambda v: float(str(v).replace("%","").strip()) if str(v).replace("%","").strip() else 0.0
    )
    df2["date_parsed"] = df2["date_raw"].apply(parse_date)
    df2["vendor"] = df2["vendor"].astype(str).str.strip()
    df2["active"] = df2["active"].astype(str).str.strip()
    df2 = df2[df2["active"].str.upper() == "Y"]
    df2 = df2[df2["vendor"].isin(["Axis", "DSP"])]
    df2 = df2[df2["n_id"].astype(str).str.strip() != ""]
    return df2.reset_index(drop=True)


def aggregate_by_fund(df, vendor, folio_key):
    sub = df[(df["vendor"] == vendor) & (df["f_id"] == folio_key)].copy()
    if sub.empty:
        return pd.DataFrame()
    grp = sub.groupby("n_id", sort=False).agg(
        invested=("invested","sum"), current=("current","sum"),
        pnl=("pnl","sum"), xirr=("xirr","mean"),
    ).reset_index()
    grp["pnl_pct"] = (grp["pnl"] / grp["invested"].replace(0,1)) * 100
    return grp


def build_table_html(rows_df, folio_label):
    if rows_df.empty:
        return ""
    cc = lambda v: "g" if float(v) >= 0 else "l"
    rows_html = ""
    for _, r in rows_df.iterrows():
        rows_html += f"""
        <tr>
          <td>{r['n_id']}</td>
          <td>{fmt_inr(r['invested'])}</td><td>{fmt_inr(r['current'])}</td>
          <td class="{cc(r['xirr'])}">{fmt_pct(r['xirr'])}</td>
          <td class="{cc(r['pnl'])}">{fmt_inr(r['pnl'])}</td>
          <td class="{cc(r['pnl_pct'])}">{fmt_pct(r['pnl_pct'])}</td>
        </tr>"""
    t_inv  = rows_df["invested"].sum()
    t_cur  = rows_df["current"].sum()
    t_pnl  = rows_df["pnl"].sum()
    t_pnlp = (t_pnl / t_inv * 100) if t_inv else 0
    t_xirr = rows_df["xirr"].mean()
    rows_html += f"""
    <tr class="tr">
      <td>Grand Total</td>
      <td>{fmt_inr(t_inv)}</td><td>{fmt_inr(t_cur)}</td>
      <td class="{cc(t_xirr)}">{fmt_pct(t_xirr)}</td>
      <td class="{cc(t_pnl)}">{fmt_inr(t_pnl)}</td>
      <td class="{cc(t_pnlp)}">{fmt_pct(t_pnlp)}</td>
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


def build_vendor_section(df, vendor, vendor_class):
    sub = df[df["vendor"] == vendor]
    if sub.empty:
        return ""
    t_inv = sub["invested"].sum()
    t_cur = sub["current"].sum()
    tables_html = ""
    for f_id, grp in sub.groupby("f_id", sort=False):
        agg = aggregate_by_fund(df, vendor, f_id)
        tables_html += build_table_html(agg, str(grp["f_id"].iloc[0]))
    return f"""
    <div class="vs">
      <div class="vh">
        <span class="vp {vendor_class}">{vendor}</span>
        <span class="vt">{vendor} Mutual Fund</span>
        <div class="vl"></div>
        <div class="vs2">Invested <b>{fmt_inr(t_inv)}</b> &nbsp;·&nbsp; Current <b>{fmt_inr(t_cur)}</b></div>
      </div>
      {tables_html}
    </div>"""


def render_mf_tab(df):
    axis_inv  = df[df["vendor"]=="Axis"]["invested"].sum()
    dsp_inv   = df[df["vendor"]=="DSP"]["invested"].sum()
    axis_cur  = df[df["vendor"]=="Axis"]["current"].sum()
    dsp_cur   = df[df["vendor"]=="DSP"]["current"].sum()
    total_cur = axis_cur + dsp_cur
    total_pnl = df["pnl"].sum()

    holdings_html = (build_vendor_section(df,"Axis","a") +
                     build_vendor_section(df,"DSP","d"))

    pts = []
    for _, r in df.iterrows():
        dt = r["date_parsed"]
        if dt is None or float(r["invested"]) <= 0:
            continue
        pts.append({"iso": dt.strftime("%Y-%m-%d"), "y": float(r["invested"]),
                    "label": str(r["n_id"]), "vendor": str(r["vendor"])})
    scatter_json = json.dumps(pts)

    dates = [d for d in df["date_parsed"] if d is not None]
    date_range = (f"{min(dates).strftime('%b %Y')} – {max(dates).strftime('%b %Y')}"
                  if dates else "")
    axis_tx = len(df[(df["vendor"]=="Axis") & df["date_parsed"].notna()])
    dsp_tx  = len(df[(df["vendor"]=="DSP")  & df["date_parsed"].notna()])
    pnl_cls = "pos" if total_pnl >= 0 else "neg"

    df_d = df[df["date_parsed"].notna()].copy()
    df_d["amt"] = df_d["invested"].astype(float)
    cards = []
    if not df_d.empty:
        lg = df_d.loc[df_d["amt"].idxmax()]
        sm = df_d.loc[df_d["amt"].idxmin()]
        df_d["ym"] = df_d["date_parsed"].apply(lambda d: d.strftime("%b %Y"))
        bm = df_d.groupby("ym")["amt"].sum()
        cards = [
            ("Total Transactions", str(len(df_d)), f"{axis_tx} Axis · {dsp_tx} DSP"),
            ("Largest Ticket", fmt_inr(lg["amt"]),
             f"{lg['date_parsed'].strftime('%d %b %Y')} · {str(lg['n_id'])[:30]}"),
            ("Smallest Ticket", fmt_inr(sm["amt"]),
             f"{sm['date_parsed'].strftime('%d %b %Y')} · {str(sm['n_id'])[:30]}"),
            ("Most Active Month", bm.idxmax(), fmt_inr(bm.max()) + " invested"),
            ("Axis Transactions", str(axis_tx), "entries"),
            ("DSP Transactions",  str(dsp_tx),  "entries"),
        ]
    insights_html = '<div class="ins">' + "".join(
        f'<div class="ic"><div class="il">{l}</div><div class="iv">{v}</div><div class="is">{s}</div></div>'
        for l,v,s in cards
    ) + "</div>"

    HTML = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;1,9..144,300;1,9..144,400&family=DM+Mono:wght@400;500&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{{--bg:#1c1c1c;--sf:#262626;--sf2:#2f2f2f;--sf3:#383838;--bd:#404040;--bd2:#505050;
  --ac:#c9933a;--adim:rgba(201,147,58,.14);--dc:#5aaee0;--ddim:rgba(90,174,224,.14);
  --gain:#4ec98a;--loss:#e05a5a;--t1:#fff;--t2:#ccc;--t3:#888;--r:14px;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:var(--bg);color:var(--t1);font-family:'Outfit',sans-serif;}}
.blob{{position:fixed;border-radius:50%;filter:blur(110px);pointer-events:none;z-index:0;}}
.b1{{width:600px;height:600px;background:rgba(201,147,58,.06);top:-180px;left:-180px;}}
.b2{{width:500px;height:500px;background:rgba(90,174,224,.06);bottom:-150px;right:-120px;}}
.wrap{{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:28px 20px 60px;}}
.hd{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:28px;gap:20px;flex-wrap:wrap;}}
.hd h1{{font-family:'Fraunces',serif;font-size:2rem;font-weight:400;letter-spacing:-.5px;}}
.hd h1 em{{font-style:italic;color:var(--ac);font-weight:300;}}
.hd p{{margin-top:6px;font-size:.68rem;color:var(--t3);font-family:'DM Mono',monospace;letter-spacing:.1em;text-transform:uppercase;}}
.kpis{{display:flex;gap:10px;flex-wrap:wrap;}}
.kpi{{background:var(--sf);border:1px solid var(--bd);border-radius:12px;padding:13px 18px;min-width:120px;position:relative;overflow:hidden;}}
.kpi::after{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:var(--ac2,var(--bd));opacity:.7;}}
.kpi.a{{--ac2:var(--ac);}} .kpi.d{{--ac2:var(--dc);}} .kpi.g{{--ac2:var(--gain);}}
.kpi-l{{font-size:.58rem;color:var(--t3);text-transform:uppercase;letter-spacing:.12em;font-family:'DM Mono',monospace;margin-bottom:5px;}}
.kpi-v{{font-family:'DM Mono',monospace;font-size:.95rem;font-weight:500;}}
.kpi-v.pos{{color:var(--gain);}} .kpi-v.neg{{color:var(--loss);}}
.tabs{{display:flex;gap:3px;background:var(--sf);border:1px solid var(--bd);border-radius:12px;padding:4px;width:fit-content;margin-bottom:24px;}}
.tb{{font-size:.8rem;font-weight:500;padding:8px 20px;border-radius:9px;border:none;background:transparent;color:var(--t3);cursor:pointer;transition:all .18s;display:flex;align-items:center;gap:7px;font-family:'Outfit',sans-serif;}}
.tb span{{width:6px;height:6px;border-radius:50%;background:currentColor;opacity:.45;}}
.tb.on{{background:var(--sf3);color:var(--t1);box-shadow:0 1px 4px rgba(0,0,0,.35);}}
.tb:hover:not(.on){{color:var(--t2);}}
.panel{{display:none;}} .panel.on{{display:block;animation:up .28s ease;}}
@keyframes up{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
.vs{{margin-bottom:36px;}}
.vh{{display:flex;align-items:center;gap:11px;margin-bottom:14px;}}
.vp{{font-size:.62rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;padding:4px 10px;border-radius:20px;font-family:'DM Mono',monospace;}}
.vp.a{{background:var(--adim);color:var(--ac);border:1px solid rgba(201,147,58,.25);}}
.vp.d{{background:var(--ddim);color:var(--dc);border:1px solid rgba(90,174,224,.25);}}
.vt{{font-size:1.1rem;font-weight:600;letter-spacing:-.2px;}}
.vl{{flex:1;height:1px;background:var(--bd);}}
.vs2{{font-family:'DM Mono',monospace;font-size:.72rem;color:var(--t3);white-space:nowrap;}}
.vs2 b{{color:var(--t2);font-weight:500;}}
.fg{{margin-bottom:18px;}}
.ft{{display:inline-flex;align-items:center;gap:6px;font-size:.64rem;color:var(--t3);text-transform:uppercase;letter-spacing:.1em;font-family:'DM Mono',monospace;margin-bottom:9px;padding:3px 10px 3px 8px;background:var(--sf2);border-radius:20px;border:1px solid var(--bd);}}
.ft::before{{content:'';width:5px;height:5px;border-radius:50%;background:var(--t3);}}
.tw{{border-radius:var(--r);border:1px solid var(--bd);overflow:hidden;background:var(--sf);}}
table{{width:100%;border-collapse:collapse;}}
thead tr{{background:var(--sf2);border-bottom:1px solid var(--bd);}}
th{{padding:10px 14px;font-size:.56rem;font-weight:600;text-transform:uppercase;letter-spacing:.12em;color:var(--t3);font-family:'DM Mono',monospace;text-align:right;white-space:nowrap;}}
th:first-child{{text-align:left;}}
tbody tr{{border-bottom:1px solid var(--bd);transition:background .1s;}}
tbody tr:last-child{{border-bottom:none;}}
tbody tr:not(.tr):hover{{background:var(--sf2);}}
td{{padding:10px 14px;font-family:'DM Mono',monospace;font-size:.75rem;text-align:right;color:var(--t2);white-space:nowrap;}}
td:first-child{{text-align:left;font-family:'Outfit',sans-serif;font-size:.78rem;color:var(--t1);max-width:260px;white-space:normal;line-height:1.45;}}
.g{{color:var(--gain)!important;}} .l{{color:var(--loss)!important;}}
.tr{{background:rgba(255,255,255,.016)!important;border-top:1px solid var(--bd2)!important;}}
.tr td{{font-weight:600;color:var(--t1)!important;}}
.tr td:first-child{{font-family:'DM Mono',monospace!important;font-size:.6rem!important;letter-spacing:.1em;text-transform:uppercase;color:var(--t3)!important;}}
.ch-hd{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px;gap:16px;flex-wrap:wrap;}}
.ch-title{{font-family:'Fraunces',serif;font-size:1.4rem;font-weight:300;letter-spacing:-.3px;}}
.ch-title em{{font-style:italic;color:var(--dc);}}
.ch-sub{{font-size:.68rem;color:var(--t3);font-family:'DM Mono',monospace;margin-top:5px;letter-spacing:.08em;text-transform:uppercase;}}
.leg{{display:flex;gap:18px;align-items:center;}}
.li{{display:flex;align-items:center;gap:8px;font-size:.78rem;color:var(--t2);}}
.ld{{width:10px;height:10px;border-radius:50%;}}
.lv{{font-family:'DM Mono',monospace;font-weight:500;}}
.cc{{background:var(--sf);border:1px solid var(--bd);border-radius:var(--r);padding:24px;position:relative;}}
.cc::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent 5%,var(--ac) 30%,var(--dc) 70%,transparent 95%);opacity:.35;border-radius:var(--r) var(--r) 0 0;}}
.cw{{position:relative;height:400px;}}
.ins{{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px;margin-top:16px;}}
.ic{{background:var(--sf);border:1px solid var(--bd);border-radius:12px;padding:14px 16px;}}
.il{{font-size:.58rem;color:var(--t3);text-transform:uppercase;letter-spacing:.1em;font-family:'DM Mono',monospace;margin-bottom:5px;}}
.iv{{font-size:1rem;font-weight:600;font-family:'DM Mono',monospace;}}
.is{{font-size:.7rem;color:var(--t3);margin-top:3px;}}
</style></head><body>
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
      <div class="kpi g"><div class="kpi-l">Overall PnL</div><div class="kpi-v {pnl_cls}">{fmt_inr(total_pnl)}</div></div>
    </div>
  </div>
  <div class="tabs">
    <button class="tb on" onclick="sw('h',this)"><span></span>Holdings</button>
    <button class="tb"    onclick="sw('t',this)"><span></span>Investment Journey</button>
  </div>
  <div class="panel on" id="p-h">{holdings_html}</div>
  <div class="panel" id="p-t">
    <div class="ch-hd">
      <div>
        <div class="ch-title">Investment <em>Scatter</em></div>
        <div class="ch-sub">Each dot = one transaction &middot; size ∝ amount &middot; {date_range}</div>
      </div>
      <div class="leg">
        <div class="li"><div class="ld" style="background:var(--ac)"></div><span>Axis</span><span class="lv" style="color:var(--ac)">{axis_tx} tx</span></div>
        <div class="li"><div class="ld" style="background:var(--dc)"></div><span>DSP</span><span class="lv" style="color:var(--dc)">{dsp_tx} tx</span></div>
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
function radius(amt){{return Math.max(5,Math.min(26,Math.sqrt(amt/500)*5));}}
function fmtD(ms){{return new Date(ms).toLocaleDateString('en-IN',{{day:'numeric',month:'short',year:'numeric'}});}}
function buildTicks(mn,mx,n){{const s=(mx-mn)/(n-1);return Array.from({{length:n}},(_,i)=>mn+i*s);}}
let drawn=false;
function drawChart(){{
  if(drawn)return;drawn=true;
  const ax=RAW.filter(d=>d.vendor==='Axis').map(d=>({{x:new Date(d.iso).getTime(),y:d.y,iso:d.iso,label:d.label,r:radius(d.y)}}));
  const ds=RAW.filter(d=>d.vendor==='DSP').map(d=>({{x:new Date(d.iso).getTime(),y:d.y,iso:d.iso,label:d.label,r:radius(d.y)}}));
  const allX=RAW.map(d=>new Date(d.iso).getTime());
  const mn=Math.min(...allX),mx=Math.max(...allX);
  new Chart(document.getElementById('chart').getContext('2d'),{{
    type:'bubble',
    data:{{datasets:[
      {{label:'Axis',data:ax,backgroundColor:'rgba(240,167,66,.55)',borderColor:'rgba(240,167,66,.88)',borderWidth:1.5,hoverBorderWidth:2}},
      {{label:'DSP', data:ds,backgroundColor:'rgba(91,188,248,.5)', borderColor:'rgba(91,188,248,.88)',borderWidth:1.5,hoverBorderWidth:2}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'#2a2a2a',borderColor:'#484848',borderWidth:1,
        titleColor:'#9499b8',bodyColor:'#e8eaf6',padding:14,
        titleFont:{{family:'DM Mono',size:11}},bodyFont:{{family:'DM Mono',size:12}},
        callbacks:{{title:i=>fmtD(i[0].raw.x),label:i=>['  '+i.dataset.label,'  ₹'+i.raw.y.toLocaleString('en-IN'),'  '+i.raw.label.replace(/_/g,' ')]}}}}}},
      scales:{{
        x:{{type:'linear',min:mn-30*864e5,max:mx+30*864e5,
          grid:{{color:'rgba(255,255,255,.06)',drawTicks:false}},
          ticks:{{color:'#555a78',font:{{family:'DM Mono',size:10}},maxRotation:0,maxTicksLimit:12,
            callback:v=>new Date(v).toLocaleDateString('en-GB',{{month:'short',year:'2-digit'}})}},
          afterBuildTicks(a){{a.ticks=buildTicks(mn,mx,12).map(v=>({{value:v}}));}},
          border:{{color:'#404040'}}}},
        y:{{title:{{display:true,text:'Amount Invested (₹)',color:'#555a78',font:{{family:'DM Mono',size:10}}}},
          grid:{{color:'rgba(255,255,255,.06)',drawTicks:false}},
          ticks:{{color:'#555a78',font:{{family:'DM Mono',size:10}},callback:v=>v>=1000?'₹'+(v/1000).toFixed(0)+'k':'₹'+v,maxTicksLimit:8}},
          border:{{color:'#404040'}}}}}}}}}}));
}}
</script></body></html>"""

    st.components.v1.html(HTML, height=1800, scrolling=True)


# ══════════════════════════════════════════════════════════════════════════
#  NPS TAB
# ══════════════════════════════════════════════════════════════════════════

def load_nps_data(uploaded_file):
    df = pd.read_csv(uploaded_file, skip_blank_lines=True)
    df.columns = [c.strip() for c in df.columns]

    def find_col(df, *names):
        for n in names:
            if n in df.columns:
                return n
        for c in df.columns:
            for n in names:
                if n.lower() in c.lower():
                    return c
        return None

    year_col  = find_col(df, "Year")
    cat_col   = find_col(df, "Category")
    fund_col  = find_col(df, "Fund Name")
    date_col  = find_col(df, "Date")
    part_col  = find_col(df, "Particulars")
    amt_col   = find_col(df, "Amount")
    nav_col   = find_col(df, "NAV")
    units_col = find_col(df, "Units")

    df2 = pd.DataFrame()
    df2["year"]        = df[year_col].astype(str).str.strip() if year_col else ""
    df2["category"]    = df[cat_col].astype(str).str.strip() if cat_col else ""
    df2["fund_name"]   = df[fund_col].astype(str).str.strip() if fund_col else ""
    df2["particulars"] = df[part_col].astype(str).str.strip() if part_col else ""
    df2["amount"]      = df[amt_col].apply(clean_num) if amt_col else 0.0
    df2["nav"]         = df[nav_col].apply(clean_num) if nav_col else 0.0
    df2["units"]       = df[units_col].apply(clean_num) if units_col else 0.0
    df2["date_parsed"] = df[date_col].apply(parse_date) if date_col else None

    df2 = df2[df2["date_parsed"].notna() & (df2["amount"] > 0)]
    return df2.reset_index(drop=True)


def render_nps_tab(df):
    # total_invested = df["amount"].sum()
    # total_units    = df["units"].sum()
    # latest_nav     = df.loc[df["date_parsed"].idxmax(), "nav"]
    # current_val    = total_units * latest_nav
    # gain           = current_val - total_invested

    # group by scheme (E, C, G)
    scheme_map = {
        "E": "Equity",
        "C": "Corporate Bond",
        "G": "Govt Sec"
    }
    
    units = {}
    invested = {}
    
    for k, v in scheme_map.items():
        sub = df[df["category"] == v]
        units[k] = sub["units"].sum()
        invested[k] = sub["amount"].sum()
    
    # fetch latest NAV
    latest_navs = {k: fetch_latest_nav(SCHEMES[k]) for k in ["E","C","G"]}
    
    summary_rows = []
    
    for k in ["E","C","G"]:
        current_val = units[k] * latest_navs[k]
    
        summary_rows.append({
            "Scheme": k,
            "Units": units[k],
            "NAV": latest_navs[k],
            "Current Value": current_val,
            "Invested": invested[k]
        })
    
    summary_df = pd.DataFrame(summary_rows)
    
    total_value = summary_df["Current Value"].sum()
    total_invested = summary_df["Invested"].sum()
    
    profit = total_value - total_invested
    profit_pct = (profit / total_invested) * 100 if total_invested else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Invested",     fmt_inr(total_invested))
    # c2.metric("Total Units",        f"{total_units:,.2f}")
    c3.metric("Latest NAV",         f"₹{latest_nav:.2f}")
    c4.metric("Est. Current Value", fmt_inr(current_val), delta=fmt_inr(gain))

    st.markdown("### Scheme Breakdown")
    
    for _, r in summary_df.iterrows():
        a_c1, a_c2, a_c3, a_c4 = st.columns(4)
        a_c1.metric(f"{r['Scheme']} Units", f"{r['Units']:.2f}")
        a_c2.metric(f"{r['Scheme']} NAV", f"₹{r['NAV']:.2f}")
        a_c3.metric(f"{r['Scheme']} Value", fmt_inr(r["Current Value"]))
        a_c4.metric(f"{r['Scheme']} Invested", fmt_inr(r["Invested"]))

    st.divider()
    st.metric(
        "Est. Current Value",
        fmt_inr(total_value),
        delta=f"{fmt_inr(profit)} ({fmt_pct(profit_pct)})"
    )

    fc1, fc2 = st.columns([3, 1])
    with fc1:
        sel_funds = st.multiselect("Fund", sorted(df["fund_name"].unique()),
                                   default=sorted(df["fund_name"].unique()), key="nps_f")
    with fc2:
        sel_cats  = st.multiselect("Category", sorted(df["category"].unique()),
                                   default=sorted(df["category"].unique()), key="nps_c")

    dff = df[df["fund_name"].isin(sel_funds) & df["category"].isin(sel_cats)].copy()
    if dff.empty:
        st.warning("No data for selected filters.")
        return

    dff = dff.sort_values("date_parsed")

    COLORS = {
        "Equity":         "#c9933a",
        "Debt":           "#5aaee0",
        "Balanced":       "#9b7fd4",
        "Corporate Bond": "#5aaee0",
        "Govt Sec":       "#4ec98a",
    }

    daily = dff.groupby("date_parsed").agg(
        units=("units","sum"), amount=("amount","sum"), nav=("nav","mean")
    ).reset_index()

    # ── Chart 1: NAV line per fund + units bar (dual axis) ────────────────
    st.markdown("### NAV Timeline & Units Acquired")
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])

    for fund in sel_funds:
        fd = dff[dff["fund_name"]==fund].sort_values("date_parsed")
        if fd.empty:
            continue
        col   = COLORS.get(fd["category"].iloc[0], "#aaaaaa")
        label = fund.split("SCHEME")[0].strip()[-45:] if "SCHEME" in fund else fund[:45]
        fig1.add_trace(go.Scatter(
            x=fd["date_parsed"], y=fd["nav"],
            mode="lines+markers", name=f"NAV · {label}",
            line=dict(color=col, width=2),
            marker=dict(size=5, color=col, opacity=0.85),
            hovertemplate="<b>%{text}</b><br>%{x|%d %b %Y}  NAV ₹%{y:.2f}<extra></extra>",
            text=[label]*len(fd),
        ), secondary_y=False)

    fig1.add_trace(go.Bar(
        x=daily["date_parsed"], y=daily["units"],
        name="Units Acquired",
        marker_color="rgba(255,255,255,0.07)",
        marker_line_color="rgba(255,255,255,0.16)", marker_line_width=1,
        hovertemplate="%{x|%d %b %Y}  Units %{y:.2f}<extra></extra>",
    ), secondary_y=True)

    fig1.update_layout(
        template="plotly_dark", paper_bgcolor="#1c1c1c", plot_bgcolor="#262626",
        font=dict(family="DM Mono, monospace", size=11, color="#cccccc"),
        legend=dict(bgcolor="rgba(30,30,30,0.9)", bordercolor="#404040",
                    borderwidth=1, font=dict(size=10)),
        margin=dict(l=60,r=60,t=20,b=50), height=460, hovermode="x unified",
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        yaxis=dict(title="NAV (₹)", gridcolor="rgba(255,255,255,0.06)",
                   zeroline=False, tickprefix="₹"),
        yaxis2=dict(title="Units Acquired", overlaying="y", side="right",
                    gridcolor="rgba(255,255,255,0.02)", zeroline=False),
        barmode="overlay",
    )
    st.plotly_chart(fig1, use_container_width=True)

    # ── Chart 2: Monthly bar + cumulative line (dual axis) ────────────────
    st.markdown("### Monthly Investment & Cumulative Total")

    dff["ym"] = dff["date_parsed"].apply(lambda d: d.replace(day=1))
    monthly = (dff.groupby("ym").agg(amount=("amount","sum"))
               .reset_index().sort_values("ym"))
    monthly["cumulative"] = monthly["amount"].cumsum()

    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(
        x=monthly["ym"], y=monthly["amount"], name="Monthly Investment",
        marker_color="rgba(201,147,58,0.5)",
        marker_line_color="rgba(201,147,58,0.8)", marker_line_width=1,
        hovertemplate="%{x|%b %Y}  ₹%{y:,.0f}<extra></extra>",
    ), secondary_y=False)

    fig2.add_trace(go.Scatter(
        x=monthly["ym"], y=monthly["cumulative"],
        mode="lines", name="Cumulative",
        line=dict(color="#4ec98a", width=2.5),
        fill="tozeroy", fillcolor="rgba(78,201,138,0.07)",
        hovertemplate="%{x|%b %Y}  Cumulative ₹%{y:,.0f}<extra></extra>",
    ), secondary_y=True)

    fig2.update_layout(
        template="plotly_dark", paper_bgcolor="#1c1c1c", plot_bgcolor="#262626",
        font=dict(family="DM Mono, monospace", size=11, color="#cccccc"),
        legend=dict(bgcolor="rgba(30,30,30,0.9)", bordercolor="#404040",
                    borderwidth=1, font=dict(size=10)),
        margin=dict(l=60,r=60,t=20,b=50), height=380, hovermode="x unified",
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        yaxis=dict(title="Amount per Month (₹)", gridcolor="rgba(255,255,255,0.06)",
                   zeroline=False, tickprefix="₹"),
        yaxis2=dict(title="Cumulative Invested (₹)", overlaying="y", side="right",
                    zeroline=False, tickprefix="₹"),
        barmode="overlay",
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Row: donut + yearly bar ───────────────────────────────────────────
    ca, cb = st.columns(2)
    with ca:
        st.markdown("### By Category")
        cg = dff.groupby("category")["amount"].sum().reset_index()
        fig3 = go.Figure(go.Pie(
            labels=cg["category"], values=cg["amount"],
            marker=dict(colors=[COLORS.get(c,"#888") for c in cg["category"]],
                        line=dict(color="#1c1c1c", width=2)),
            hole=0.44,
            textfont=dict(family="DM Mono, monospace", size=11),
            hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}  %{percent}<extra></extra>",
        ))
        fig3.update_layout(
            paper_bgcolor="#1c1c1c", margin=dict(l=10,r=10,t=20,b=10),
            height=320, font=dict(family="DM Mono, monospace", size=11, color="#ccc"),
            legend=dict(bgcolor="rgba(30,30,30,0.9)", bordercolor="#404040",
                        borderwidth=1, font=dict(size=10)),
        )
        st.plotly_chart(fig3, use_container_width=True)

    with cb:
        st.markdown("### Yearly Investment")
        yg = dff.groupby("year")["amount"].sum().reset_index().sort_values("year")
        fig4 = go.Figure(go.Bar(
            x=yg["year"], y=yg["amount"],
            marker_color="#5aaee0",
            marker_line_color="rgba(90,174,224,0.5)", marker_line_width=1,
            text=[fmt_inr(v) for v in yg["amount"]],
            textposition="outside",
            textfont=dict(size=10, color="#cccccc"),
            hovertemplate="Year %{x}  ₹%{y:,.0f}<extra></extra>",
        ))
        fig4.update_layout(
            template="plotly_dark", paper_bgcolor="#1c1c1c", plot_bgcolor="#262626",
            font=dict(family="DM Mono, monospace", size=11, color="#ccc"),
            margin=dict(l=40,r=20,t=20,b=40), height=320,
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False, tickprefix="₹"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False, type="category"),
        )
        st.plotly_chart(fig4, use_container_width=True)

    with st.expander("Raw Transaction Data"):
        show = dff[["date_parsed","year","category","fund_name",
                    "particulars","amount","nav","units"]].copy()
        show["date_parsed"] = show["date_parsed"].apply(lambda d: d.strftime("%d %b %Y"))
        show["amount"] = show["amount"].apply(fmt_inr)
        show.columns = ["Date","Year","Category","Fund","Particulars","Amount","NAV","Units"]
        st.dataframe(show, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
#  GLOBAL STYLES
# ══════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
[data-testid="stAppViewContainer"]  { background: #1c1c1c; }
[data-testid="stHeader"]            { background: transparent; }
[data-testid="stSidebar"]           { display: none; }
section.main > div                  { padding-top: 1.5rem; }
[data-testid="stMetric"]            { background:#262626; border:1px solid #404040; border-radius:12px; padding:14px 18px; }
[data-testid="stMetricLabel"] p     { color:#888 !important; font-size:.7rem !important; font-family:'DM Mono',monospace !important; text-transform:uppercase; letter-spacing:.08em; }
[data-testid="stMetricValue"]       { color:#fff !important; font-family:'DM Mono',monospace !important; }
[data-testid="stMetricDelta"]       { font-family:'DM Mono',monospace !important; font-size:.8rem !important; }
[data-testid="stFileUploader"]      { background:#262626; border:1px dashed #505050; border-radius:14px; padding:16px 20px; }
[data-testid="stFileUploader"] *    { color:#ccc !important; }
.stTabs [data-baseweb="tab-list"]   { background:#262626; border-radius:12px; padding:4px; border:1px solid #3a3a3a; gap:3px; width:fit-content; }
.stTabs [data-baseweb="tab"]        { background:transparent; border-radius:9px; color:#888; font-family:'Outfit',sans-serif; font-size:.85rem; padding:8px 26px; }
.stTabs [aria-selected="true"]      { background:#383838 !important; color:#fff !important; }
.stTabs [data-baseweb="tab-border"] { display:none; }
.stTabs [data-baseweb="tab-panel"]  { padding-top: 24px; }
hr                                  { border-color:#3a3a3a; margin: 16px 0; }
h3                                  { font-family:'Outfit',sans-serif !important; font-size:1rem !important; font-weight:600 !important; color:#cccccc !important; letter-spacing:-.2px; margin-bottom:4px; }
div[data-testid="stMarkdownContainer"] p { color:#ccc; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
#  APP HEADER
# ══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="margin-bottom:24px;">
  <div style="font-family:'Fraunces',Georgia,serif;font-size:2.2rem;font-weight:400;
       color:#fff;letter-spacing:-.5px;line-height:1.1;">
    Portfolio <em style="font-style:italic;color:#c9933a;font-weight:300;">Tracker</em>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:.68rem;color:#555;
       text-transform:uppercase;letter-spacing:.12em;margin-top:7px;">
    Mutual Funds &nbsp;·&nbsp; NPS &nbsp;·&nbsp; Upload a CSV in each tab
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
#  TWO INDEPENDENT TABS
# ══════════════════════════════════════════════════════════════════════════

tab_mf, tab_nps = st.tabs(["📊  Mutual Funds", "🏛️  NPS"])

# ── MF tab ─────────────────────────────────────────────────────────────────
with tab_mf:
    mf_file = st.file_uploader(
        "Upload MF Tracker CSV",
        type=["csv"], key="mf_upload",
        help="Expected columns: Vendor, Active, N Identifier, F Identifier, Date, Invested Amount, Current Amount, Profit, Absolute Profit %, XIRR",
    )
    if mf_file:
        try:
            mf_df = load_mf_data(mf_file)
            if mf_df.empty:
                st.warning("No active Axis/DSP holdings found. Check Vendor names and Active column.")
            else:
                render_mf_tab(mf_df)
        except Exception as e:
            st.error(f"Could not parse MF CSV: {e}")
            st.exception(e)
    else:
        st.markdown("""
        <div style="text-align:center;padding:70px 0 50px;color:#444;
             font-family:'DM Mono',monospace;font-size:.8rem;letter-spacing:.08em;line-height:2;">
          Upload a CSV above to view your Mutual Fund holdings &amp; investment journey<br>
          <span style="color:#333;font-size:.7rem;">
            Vendor · Active · N Identifier · F Identifier · Date<br>
            Invested Amount · Current Amount · Profit · Absolute Profit % · XIRR
          </span>
        </div>""", unsafe_allow_html=True)

# ── NPS tab ────────────────────────────────────────────────────────────────
with tab_nps:
    nps_file = st.file_uploader(
        "Upload NPS Tracker CSV",
        type=["csv"], key="nps_upload",
        help="Expected columns: Year, Category, Fund Name, Date, Particulars, Amount, NAV, Units",
    )
    if nps_file:
        try:
            nps_df = load_nps_data(nps_file)
            if nps_df.empty:
                st.warning("No valid NPS rows found. Check Date format and Amount column.")
            else:
                render_nps_tab(nps_df)
        except Exception as e:
            st.error(f"Could not parse NPS CSV: {e}")
            st.exception(e)
    else:
        st.markdown("""
        <div style="text-align:center;padding:70px 0 50px;color:#444;
             font-family:'DM Mono',monospace;font-size:.8rem;letter-spacing:.08em;line-height:2;">
          Upload a CSV above to view your NPS investment charts<br>
          <span style="color:#333;font-size:.7rem;">
            Year · Category · Fund Name · Date · Particulars · Amount · NAV · Units
          </span>
        </div>""", unsafe_allow_html=True)
