import streamlit as st

from mf.aggregator import aggregate_by_fund
from utils.helpers import fmt_inr, fmt_pct, fmt_float


def _fund_table(rows_df):
    table = rows_df[["n_id", "invested", "current", "xirr", "pnl", "pnl_pct"]].copy()
    table.columns = ["Fund", "Invested", "Current", "XIRR", "PnL", "PnL %"]
    return table


def _show_vendor_holdings(df, vendor):
    vendor_df = df[df["vendor"] == vendor]
    if vendor_df.empty:
        return

    st.subheader(f"{vendor} Mutual Fund")
    summary_cols = st.columns(4)
    summary_cols[0].metric("Invested", fmt_inr(vendor_df["invested"].sum()))
    summary_cols[1].metric("Current", fmt_inr(vendor_df["current"].sum()))
    summary_cols[3].metric("XIRR", fmt_pct(vendor_df["xirr"].mean()))

    current = vendor_df["current"].sum()
    old = vendor_df["invested"].sum()
    tmp_delta = ((current - old) / old) * 100
    total_pnl = vendor_df["pnl"].sum()
    summary_cols[2].metric("Overall PnL", fmt_inr(total_pnl), delta=fmt_pct(tmp_delta))

    for f_id, group in vendor_df.groupby("f_id", sort=False):
        st.markdown("#### " + str(f_id))
        aggregate = aggregate_by_fund(df, vendor, f_id)
        st.dataframe(_fund_table(aggregate), hide_index=True, use_container_width=True)


def render_holdings_tab(df):
    total_pnl = df["pnl"].sum()

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Invested", fmt_inr(df["invested"].sum()))
    metric_cols[1].metric("Total Current", fmt_inr(df["current"].sum()))

    current = df["current"].sum()
    old = df["invested"].sum()
    tmp_delta = ((current - old) / old) * 100
    metric_cols[2].metric("Overall PnL", fmt_inr(total_pnl), delta=fmt_pct(tmp_delta))

    metric_cols[3].metric("Avg Years", fmt_float(df["delta_date"].mean() / 360))

    holdings_axis_tab, holdings_dsp_tab = st.tabs(["Axis", "DSP"])
    with holdings_axis_tab:
        _show_vendor_holdings(df, "Axis")
    with holdings_dsp_tab:
        _show_vendor_holdings(df, "DSP")