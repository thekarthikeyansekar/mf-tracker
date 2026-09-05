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
    dated_rows = sub[sub["date_parsed"].notna()]
    v_xirr = sub["xirr"].mean()
    if len(dated_rows) > 1:
        v_years = ((dated_rows["date_parsed"].max() -
                    dated_rows["date_parsed"].min()).days / 365.25)
    else:
        v_years = 0
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
        <div class="vs2">Invested <b>{fmt_inr(t_inv)}</b> &nbsp;·&nbsp; Current <b>{fmt_inr(t_cur)}</b> &nbsp;·&nbsp; XIRR <b class="{('g' if v_xirr >= 0 else 'l')}">{fmt_pct(v_xirr)}</b> &nbsp;·&nbsp; Years <b>{v_years:.1f}</b></div>
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

    fund_plots = []
    for fund, group in df.groupby("n_id", sort=False):
      dated = group[
          group["date_parsed"].notna() & (group["nav"] > 0)
      ].sort_values("date_parsed")
      points = [
        {"x": row["date_parsed"].strftime("%Y-%m-%d"),
         "y": float(row["bought_nav"]),
         "vendor": str(row["vendor"])}
        for _, row in dated.iterrows()
      ]
      nav_rows = dated[dated["nav"] > 0]
      current_nav = float(nav_rows.iloc[-1]["nav"]) if not nav_rows.empty else None
      if points:
        fund_plots.append({"name": str(fund), "vendor": str(group["vendor"].iloc[0]),
               "points": points, "current_nav": current_nav})
    fund_plots_json = json.dumps(fund_plots)
    fund_vendors = [vendor for vendor in ("Axis", "DSP")
                    if any(plot["vendor"] == vendor for plot in fund_plots)]
    fund_vendor_tabs = "".join(
        f'<button class="fund-vendor-tab{" on" if i == 0 else ""}" '
        f'onclick="window.showFundVendor(\'{vendor}\',this)">{vendor}</button>'
        for i, vendor in enumerate(fund_vendors)
    )
    fund_vendor_panels = "".join(
        f'<div class="fund-vendor-panel{" on" if i == 0 else ""}" id="fp-{vendor}">'
        f'<div class="fund-grid" id="fund-grid-{vendor}"></div></div>'
        for i, vendor in enumerate(fund_vendors)
    )

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
            ("Largest Amount", fmt_inr(lg["amt"]),
             f"{lg['date_parsed'].strftime('%d %b %Y')} · {str(lg['n_id'])[:30]}"),
            ("Smallest Amount", fmt_inr(sm["amt"]),
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
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{{--bg:#1c1c1c;--sf:#262626;--sf2:#2f2f2f;--sf3:#383838;--bd:#404040;--bd2:#505050;
  --ac:#c9933a;--adim:rgba(201,147,58,.14);--dc:#5aaee0;--ddim:rgba(90,174,224,.14);
  --gain:#4ec98a;--loss:#e05a5a;--t1:#fff;--t2:#ccc;--t3:#888;--r:14px;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:var(--bg);color:var(--t1);font-family:'Outfit',sans-serif;}}
.blob{{position:fixed;border-radius:50%;filter:blur(110px);pointer-events:none;z-index:0;}}
.b1{{width:600px;height:600px;background:rgba(201,147,58,.06);top:-180px;left:-180px;}}
.b2{{width:500px;height:500px;background:rgba(90,174,224,.06);bottom:-150px;right:-120px;}}
.wrap{{position:relative;z-index:1;width:100%;max-width:none;margin:0;padding:32px clamp(24px,4vw,64px) 72px;}}
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
.vs2{{font-family:'DM Mono',monospace;font-size:.72rem;color:var(--t3);white-space:normal;text-align:right;line-height:1.7;}}
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
.cc{{background:var(--sf);border:1px solid var(--bd);border-radius:var(--r);padding:28px;position:relative;}}
.cc::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent 5%,var(--ac) 30%,var(--dc) 70%,transparent 95%);opacity:.35;border-radius:var(--r) var(--r) 0 0;}}
.cw{{position:relative;height:440px;}}
.ins{{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px;margin-top:16px;}}
.ic{{background:var(--sf);border:1px solid var(--bd);border-radius:12px;padding:14px 16px;}}
.il{{font-size:.58rem;color:var(--t3);text-transform:uppercase;letter-spacing:.1em;font-family:'DM Mono',monospace;margin-bottom:5px;}}
.iv{{font-size:1rem;font-weight:600;font-family:'DM Mono',monospace;}}
.is{{font-size:.7rem;color:var(--t3);margin-top:3px;}}
.fund-grid{{display:grid;grid-template-columns:repeat(2,minmax(360px,1fr));gap:24px;}}
.fund-vendor-tabs{{display:flex;gap:4px;margin-bottom:20px;}}
.fund-vendor-tab{{background:var(--sf2);border:1px solid var(--bd);border-radius:9px;color:var(--t3);cursor:pointer;font-family:'DM Mono',monospace;font-size:.68rem;padding:9px 18px;text-transform:uppercase;}}
.fund-vendor-tab.on{{background:var(--sf3);color:var(--t1);border-color:var(--bd2);}}
.fund-vendor-panel{{display:none;}} .fund-vendor-panel.on{{display:block;animation:up .22s ease;}}
.fund-card{{background:var(--sf);border:1px solid var(--bd);border-radius:var(--r);padding:22px;min-width:0;}}
.fund-card-hd{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px;}}
.fund-name{{font-size:.85rem;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.fund-nav{{font-family:'DM Mono',monospace;font-size:.68rem;color:var(--loss);white-space:nowrap;}}
.fund-cw{{height:320px;position:relative;}}
.fund-note{{font-size:.68rem;color:var(--t3);margin-bottom:14px;}}
@media(max-width:900px){{.fund-grid{{grid-template-columns:1fr;}}.vs2{{text-align:left;}}}}
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
    <button class="tb on" onclick="window.sw('h',this)"><span></span>Holdings</button>
    <button class="tb"    onclick="window.sw('t',this)"><span></span>Investment Journey</button>
    <button class="tb"    onclick="window.sw('f',this)"><span></span>Fund-wise Tracker</button>
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
    <div class="cc"><div class="cw" id="chart"></div></div>
    {insights_html}
  </div>
  <div class="panel" id="p-f">
    <div class="ch-hd">
      <div>
        <div class="ch-title">Fund-wise <em>Investment Tracker</em></div>
        <div class="ch-sub">One plot per fund &middot; invested NAV by transaction date</div>
      </div>
    </div>
    <div class="fund-note">The red dotted line marks the latest NAV when a NAV column is provided in the CSV.</div>
    <div class="fund-vendor-tabs">{fund_vendor_tabs}</div>
    {fund_vendor_panels}
  </div>
</div>
<script>
window.sw = function(id,btn){{
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));
  document.querySelectorAll('.tb').forEach(b=>b.classList.remove('on'));
  document.getElementById('p-'+id).classList.add('on');
  btn.classList.add('on');
  if(id==='t') setTimeout(drawChart,80);
  if(id==='f') setTimeout(drawFundCharts,80);
}};
window.showFundVendor = function(vendor,btn){{
  document.querySelectorAll('.fund-vendor-panel').forEach(p=>p.classList.remove('on'));
  document.querySelectorAll('.fund-vendor-tab').forEach(b=>b.classList.remove('on'));
  document.getElementById('fp-'+vendor).classList.add('on');
  btn.classList.add('on');
}};
</script>
<script>
const RAW={scatter_json};
const FUND_RAW={fund_plots_json};
function radius(amt){{return Math.max(5,Math.min(26,Math.sqrt(amt/500)*5));}}
function fmtD(ms){{return new Date(ms).toLocaleDateString('en-IN',{{day:'numeric',month:'short',year:'numeric'}});}}
function buildTicks(mn,mx,n){{const s=(mx-mn)/(n-1);return Array.from({{length:n}},(_,i)=>mn+i*s);}}
let drawn=false;
let fundChartsDrawn=false;
function drawChart(){{
  if(drawn)return;drawn=true;
  const makeTrace=(vendor,color)=>{{
    const rows=RAW.filter(d=>d.vendor===vendor);
    return {{x:rows.map(d=>d.iso),y:rows.map(d=>d.y),mode:'markers',name:vendor,
      marker:{{size:rows.map(d=>radius(d.y)),color:color,opacity:.72,line:{{color:color,width:1}}}},
      customdata:rows.map(d=>d.label),
      hovertemplate:'%{{x|%d %b %Y}}<br>'+vendor+': ₹%{{y:,.0f}}<br>%{{customdata}}<extra></extra>'}};
  }};
  Plotly.newPlot('chart',[makeTrace('Axis','#f0a742'),makeTrace('DSP','#5bbcf8')],{{
    margin:{{l:65,r:20,t:10,b:45}},paper_bgcolor:'transparent',plot_bgcolor:'transparent',
    font:{{family:'DM Mono',color:'#888',size:10}},hovermode:'closest',showlegend:false,
    xaxis:{{type:'date',gridcolor:'rgba(255,255,255,.06)',zeroline:false,tickformat:'%b %y',color:'#555a78'}},
    yaxis:{{title:{{text:'Amount Invested (₹)',font:{{size:10}}}},range:[0,20000],
      gridcolor:'rgba(255,255,255,.06)',zeroline:false,color:'#555a78',tickformat:'₹,.0f'}}
  }},{{responsive:true,scrollZoom:true,displaylogo:false,
    modeBarButtonsToAdd:['zoom2d','pan2d','resetScale2d'],modeBarButtonsToRemove:['lasso2d','select2d']}});
}}
function drawFundCharts(){{
  if(fundChartsDrawn)return;
  fundChartsDrawn=true;
  FUND_RAW.forEach((fund,index)=>{{
    const grid=document.getElementById('fund-grid-'+fund.vendor);
    if(!grid)return;
    if(grid.dataset.drawn!=='1')grid.dataset.drawn='1';
    const card=document.createElement('div');
    card.className='fund-card';
    const header=document.createElement('div');
    header.className='fund-card-hd';
    const name=document.createElement('div');
    name.className='fund-name';
    name.textContent=fund.name;
    const nav=document.createElement('div');
    nav.className='fund-nav';
    nav.textContent=fund.current_nav===null?'NAV unavailable':'NAV ₹'+fund.current_nav.toLocaleString('en-IN');
    header.append(name,nav);
    const chartWrap=document.createElement('div');
    chartWrap.className='fund-cw';
    chartWrap.id='fund-chart-'+index;
    card.append(header,chartWrap);
    grid.appendChild(card);
    const dates=fund.points.map(p=>p.x);
    const invested=fund.points.map(p=>p.y);
    const traces=[{{x:dates,y:invested,mode:'markers',name:'Invested',
      marker:{{size:9,color:'#c9933a',line:{{color:'#f0c477',width:1}}}},
      hovertemplate:'Date: %{{x|%d %b %Y}}<br>Invested NAV: ₹%{{y:,.2f}}<extra></extra>'}}];
    if(fund.current_nav!==null){{
      traces.push({{x:[dates[0],dates[dates.length-1]],y:[fund.current_nav,fund.current_nav],
        mode:'lines',name:'Current NAV',line:{{color:'#e05a5a',dash:'dot',width:2}},
        hovertemplate:'Current NAV: ₹%{{y:,.2f}}<extra></extra>'}});
    }}
    Plotly.newPlot(chartWrap,traces,{{
      margin:{{l:58,r:18,t:8,b:45}},paper_bgcolor:'transparent',plot_bgcolor:'transparent',
      font:{{family:'DM Mono',color:'#888',size:10}},hovermode:'closest',
      showlegend:fund.current_nav!==null,
      legend:{{orientation:'h',y:1.12,x:0,font:{{size:10}}}},
      xaxis:{{type:'date',gridcolor:'rgba(255,255,255,.06)',zeroline:false,
        tickformat:'%b %y',color:'#555a78',rangeslider:{{visible:false}}}},
      yaxis:{{title:{{text:'Invested NAV (₹)',font:{{size:10}}}},rangemode:'tozero',
        gridcolor:'rgba(255,255,255,.06)',zeroline:false,color:'#555a78',tickformat:'₹,.0f'}}
    }},{{responsive:true,scrollZoom:true,displaylogo:false,
      modeBarButtonsToAdd:['zoom2d','pan2d','resetScale2d'],modeBarButtonsToRemove:['lasso2d','select2d']}});
  }});
}}
</script></body></html>"""

    component_height = max(1800, 720 + ((len(fund_plots) + 1) // 2) * 430)
    st.components.v1.html(HTML, height=component_height, scrolling=True)
