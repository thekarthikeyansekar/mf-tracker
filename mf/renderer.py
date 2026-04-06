import streamlit as st
from utils.helpers import fmt_inr, fmt_pct
from mf.aggregator import aggregate_by_fund
import json

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
