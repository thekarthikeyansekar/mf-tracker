import streamlit as st
from utils.helpers import fmt_inr, fmt_pct
from utils.finance import xirr, fetch_latest_nav
from config.constants import SCHEMES
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


xirr_results = {}

def render_nps_tab(df):
    # total_invested = df["amount"].sum()
    # total_units    = df["units"].sum()
    # latest_nav     = df.loc[df["date_parsed"].idxmax(), "nav"]
    # current_val    = total_units * latest_nav
    # gain           = current_val - total_invested

    # group by scheme (E, C, G)
    scheme_map = {
        "E": "Equity",
        "C": "Corporate Bonds",
        "G": "Government"
    }
    
    units = {}
    invested = {}

    # st.write(df)
    # st.write(df['category'].unique())

    # fetch latest NAV
    latest_navs = {k: fetch_latest_nav(SCHEMES[k]) for k in ["E","C","G"]}
    summary_rows = []
    
    for k, v in scheme_map.items():
        latest_nav = latest_navs.get(k)

        sub = df[df["category"] == v]
        units[k] = sub["units"].sum()
        invested[k] = sub["amount"].sum()

        df.loc[df["category"] == v, 'current_nav'] = latest_nav

        if latest_nav is None:
            xirr_results[k] = 0
            latest_nav = sub['nav'].values[-1]

        # cashflows = []

        # investments (negative)
        # for _, row in sub.iterrows():
        #     cashflows.append((row["date_parsed"], -row["amount"]))
        
        cashflows = list(zip(sub["date_parsed"], -sub["amount"]))

        # current value (positive, today)
        current_val = units[k] * latest_nav
        from datetime import date
        cashflows.append((date.today(), current_val))
        
        if not (any(cf < 0 for _, cf in cashflows) and any(cf > 0 for _, cf in cashflows)):
            xirr_results[k] = 0
            continue

        try:
            xirr_results[k] = xirr(cashflows)
        except Exception as e:
            print(f"XIRR error for {k}: {e}")
            xirr_results[k] = 0
    
    # for k in ["E","C","G"]:

        summary_rows.append({
            "Scheme": k,
            "Units": units[k],
            "NAV": latest_navs[k],
            "Current Value": current_val,
            "Invested": invested[k],
            "Profit" : current_val - invested[k],
            "Profit_Perc" : ((current_val - invested[k]) / invested[k]) * 100,
            "XIRR" : xirr_results[k]
        })
        
    
    summary_df = pd.DataFrame(summary_rows)
    
    total_value = summary_df["Current Value"].sum()
    total_invested = summary_df["Invested"].sum()
    
    profit = total_value - total_invested
    profit_pct = (profit / total_invested) * 100 if total_invested else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Invested",     fmt_inr(total_invested))
    c2.metric(
        "Est. Current Value",
        fmt_inr(total_value),
        delta=f"{fmt_inr(profit)} ({fmt_pct(profit_pct)})"
    )

    # c2.metric("Total Units",        f"{total_units:,.2f}")
    # c3.metric("Latest NAV",         f"₹{latest_nav:.2f}")
    # c4.metric("Est. Current Value", fmt_inr(current_val), delta=fmt_inr(gain))

    st.markdown("### Scheme Breakdown")
    
    for _, r in summary_df.iterrows():
        a_c1, a_c2, a_c3, a_c4, a_c5, a_c6 = st.columns(6)
        a_c1.metric(f"{r['Scheme']} Units", f"{r['Units']:.2f}")
        a_c2.metric(f"{r['Scheme']} NAV", f"₹{r['NAV']:.2f}")
        a_c3.metric(f"{r['Scheme']} Current Value", fmt_inr(r["Current Value"]))
        a_c4.metric(f"{r['Scheme']} Invested", fmt_inr(r["Invested"]))
        a_c5.metric(f"{r['Scheme']} Profit", fmt_inr(r["Profit"]))
        a_c6.metric(f"{r['Scheme']} Profit %", fmt_pct(r["Profit_Perc"]))
        # a_c7.metric(f"{r['Scheme']} XIRR", fmt_pct(r["XIRR"]))

    fc1, fc2 = st.columns([3, 1])
    with fc1:
        sel_cats  = st.multiselect("Category", sorted(df["category"].unique()),
                                   default=sorted(df["category"].unique()), key="nps_c")
    with fc2:
        sel_funds = st.multiselect("Fund", sorted(df["fund_name"].unique()),
                                   default=sorted(df["fund_name"].unique()), key="nps_f")

    dff = df[df["fund_name"].isin(sel_funds) & df["category"].isin(sel_cats)].copy()
    if dff.empty:
        st.warning("No data for selected filters.")
        return

    dff = dff.sort_values("date_parsed")

    dff["current_value"] = dff["units"] * dff["current_nav"]
    dff["profit"] = dff["current_value"] - dff["amount"]

    COLORS = {
        "Equity":         "#c9933a",
        "Debt":           "#5aaee0",
        "Balanced":       "#9b7fd4",
        "Corporate Bonds": "#5aaee0",
        "Government":       "#4ec98a",
    }

    daily = dff.groupby("date_parsed").agg(
        units=("units","sum"), amount=("amount","sum"), nav=("nav","mean")
    ).reset_index()

    # ── Chart 0: Yearly Investment ────────────────

    st.markdown("### Yearly Investment")
    dff['years_count'] = date.today().year - dff['date_parsed'].dt.year
    dff.loc[dff['years_count'] <=0, 'years_count'] = 1

    yearly = (
        dff.groupby("year")
        .agg(
            invested=("amount", "sum"),
            current_value=("current_value", "sum"),
            profit=("profit", "sum"),
            years_count=("years_count", "min")
        )
        .reset_index()
        .sort_values("year")
    )
    yearly["profit_per"] = np.round(yearly["profit"] / yearly["invested"], 4) 
    yearly["profit_per_yearly"] = np.round((yearly["profit_per"] / yearly["years_count"]) * 100, 0) 
    yearly["profit_per"] = np.round(yearly["profit_per"]*100,2)

    st.dataframe(yearly)

    fig_0 = go.Figure()

    fig_0.add_trace(go.Bar(
        x=yearly["year"], y=yearly["invested"],
        marker_color="#5aaee0",
        marker_line_color="rgba(90,174,224,0.5)", marker_line_width=1,
        text=[fmt_inr(v) for v in yearly["invested"]],
        textposition="outside",
        textfont=dict(size=10, color="#cccccc"),
        hovertemplate="Year %{x}  ₹%{y:,.0f}<extra></extra>",
        
        name='Invested'
    ))

    fig_0.add_trace(go.Bar(
        x=yearly["year"],
        y=yearly["current_value"],
        name="Current Value",
        marker_color="rgba(78,201,138,0.7)",
        # hovertemplate="Year %{x}  ₹%{y:,.0f}<extra></extra>",
        text=[fmt_inr(v) for v in yearly["current_value"]],
        textposition="outside",
        customdata=np.stack([
            yearly["profit_per"],
            yearly["profit_per_yearly"]    # %
        ], axis=-1),
        hovertemplate=(
            "Year %{x}<br>"
            "Profit: ₹%{y:,.0f}<br>"
            "Return: %{customdata[0]:.0f}%<br>"
            "Annualized: %{customdata[1]:,.0f}%"
            "<extra></extra>"
        ),
    ))

    fig_0.add_trace(go.Bar(
        x=yearly["year"],
        y=yearly["profit"],
        name="Profit",
        marker_color="#e6c222",
        hovertemplate="₹%{y:,.0f}<extra></extra>",
        text=[fmt_inr(v) for v in yearly["profit"]],
        textposition="outside"
    ))

    fig_0.update_layout(
        template="plotly_dark", paper_bgcolor="#1c1c1c", plot_bgcolor="#262626",
        font=dict(family="DM Mono, monospace", size=11, color="#ccc"),
        margin=dict(l=40,r=20,t=20,b=40), height=320,
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False, tickprefix="₹"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False, type="category"),
    )
    st.plotly_chart(fig_0, width='stretch')

    # ── Chart 0: Yearly Investment (Only Profit) ────────────────
    st.markdown("### Yearly Profit and XIRR %")


    fig_0_2 = go.Figure()

    fig_0_2.add_trace(go.Bar(
        x=yearly["year"], y=yearly["profit_per"],
        marker_color="#5aaee0",
        marker_line_color="rgba(90,174,224,0.5)", marker_line_width=1,
        text=[fmt_pct(v) for v in yearly["profit_per"]],
        textposition="outside",
        textfont=dict(size=10, color="#cccccc"),
        hovertemplate="%{y:,.0f}<extra></extra>",
        
        name='Profit %'
    ))
    fig_0_2.add_trace(go.Bar(
        x=yearly["year"],
        y=yearly["profit_per_yearly"],
        name="Profit % Yearly",
        marker_color="rgba(78,201,138,0.7)",
        text=[fmt_pct(v) for v in yearly["profit_per_yearly"]],
        textposition="outside",
        hovertemplate="%{y:,.0f}<extra></extra>"
        # secondary_y=True
    ))
    fig_0_2.update_layout(
        template="plotly_dark", paper_bgcolor="#1c1c1c", plot_bgcolor="#262626",
        font=dict(family="DM Mono, monospace", size=11, color="#ccc"),
        margin=dict(l=40,r=20,t=20,b=40), height=320,
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False, type="category"),
    )
  
    st.plotly_chart(fig_0_2, width='stretch')


    # ── Chart 1: NAV line per fund + units bar (dual axis) ────────────────
    st.markdown("### Investment Timeline")
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])

    for fund in sel_funds:
        fd = dff[dff["fund_name"]==fund].sort_values("date_parsed")
        if fd.empty:
            continue
        col = COLORS.get(fd["category"].iloc[0], "#aaaaaa")
        # label = fund.split("SCHEME")[0].strip()[-45:] if "SCHEME" in fund else fund[:45]
        label = fund.split("SCHEME")[-1].strip() if "SCHEME" in fund else fund
        # label = fund
        fig1.add_trace(go.Scatter(
            x=fd["date_parsed"], y=fd["nav"],
            mode="lines+markers", name=f"NAV · {label}",
            line=dict(color=col, width=2),
            marker=dict(size=5, color=col, opacity=0.85),
            hovertemplate="<b>%{text}</b><br>%{x|%d %b %Y}  NAV ₹%{y:.2f}<extra></extra>",
            text=[label]*len(fd),
        ), secondary_y=False)

        # fig1.add_trace(go.Bar(
        #     x=fd["date_parsed"], y=fd["units"],
        #     name="Units Acquired",
        #     marker_color=col,
        #     hovertemplate="%{x|%d %b %Y}  Units %{y:.2f}<extra></extra>",
        # ), secondary_y=True)

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
    st.plotly_chart(fig1, width='stretch')

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
    st.plotly_chart(fig2, width='stretch')

    # ── Chart 3: Profit Chart
    st.markdown("### Profit Graph")
    

    st.dataframe(dff)

    dff["month"] = dff["date_parsed"].dt.year.astype(str) + "_" + dff["date_parsed"].dt.month.astype(str)

    monthly = (
        dff.groupby("month")
        .agg(
            invested=("amount", "sum"),
            current_value=("current_value", "sum"),
            profit=("profit", "sum")
        )
        .reset_index()
        .sort_values("month")
    )

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=monthly["month"],
        y=monthly["invested"],
        name="Invested",
        marker_color="rgba(201,147,58,0.6)",
    ))

    fig.add_trace(go.Bar(
        x=monthly["month"],
        y=monthly["current_value"],
        name="Current Value",
        marker_color="rgba(78,201,138,0.7)",
    ))

    fig.update_layout(
        barmode="group",
        template="plotly_dark",
        yaxis=dict(title="₹ Amount", tickprefix="₹"),
        hovermode="x unified"
    )
    st.plotly_chart(fig, width='stretch')

    # monthly = (
    #     dff.groupby("ym")
    #     .agg(
    #         p_invested=("nav", "mean"),
    #         p_current_value=("current_nav", "mean")
    #     )
    #     .reset_index()
    #     .sort_values("ym")
    # )

    # fig = go.Figure()

    # fig.add_trace(go.Bar(
    #     x=monthly["ym"],
    #     y=monthly["p_invested"],
    #     name="Invested",
    #     marker_color="rgba(201,147,58,0.6)",
    # ))

    # fig.add_trace(go.Bar(
    #     x=monthly["ym"],
    #     y=monthly["p_current_value"],
    #     name="Current NAV",
    #     marker_color="rgba(78,201,138,0.7)",
    # ))

    # fig.update_layout(
    #     barmode="group",
    #     template="plotly_dark",
    #     yaxis=dict(title="₹ NAV", tickprefix="₹"),
    #     hovermode="x unified"
    # )
    # st.plotly_chart(fig, width='stretch')
    

    # ── Row: donut + yearly bar ───────────────────────────────────────────
    # ca, cb = st.columns(2)
    # with ca:
        # st.markdown("### By Category")
        # cg = dff.groupby("category")["amount"].sum().reset_index()
        # fig3 = go.Figure(go.Pie(
        #     labels=cg["category"], values=cg["amount"],
        #     marker=dict(colors=[COLORS.get(c,"#888") for c in cg["category"]],
        #                 line=dict(color="#1c1c1c", width=2)),
        #     hole=0.44,
        #     textfont=dict(family="DM Mono, monospace", size=11),
        #     hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}  %{percent}<extra></extra>",
        # ))
        # fig3.update_layout(
        #     paper_bgcolor="#1c1c1c", margin=dict(l=10,r=10,t=20,b=10),
        #     height=320, font=dict(family="DM Mono, monospace", size=11, color="#ccc"),
        #     legend=dict(bgcolor="rgba(30,30,30,0.9)", bordercolor="#404040",
        #                 borderwidth=1, font=dict(size=10)),
        # )
        # st.plotly_chart(fig3, width='stretch')

    # with cb:

    