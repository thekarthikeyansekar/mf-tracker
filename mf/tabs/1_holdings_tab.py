from datetime import date
from scipy.optimize import brentq
import streamlit as st
import pandas as pd
import numpy as np
from mf.aggregator import aggregate_by_fund
from utils.finance import xirr
from utils.helpers import fmt_inr, fmt_pct, fmt_float


# def xirr_custom(cash_flows, dates):
#     """
#     Calculate XIRR for irregular cash flows.

#     cash_flows: list of numbers
#         Investments = negative
#         Redemptions/current value = positive

#     dates: list of date objects
#         Corresponding dates for each cash flow.
#     """

#     if len(cash_flows) != len(dates):
#         raise ValueError("cash_flows and dates must have the same length")

#     first_date = dates[0]

#     def xnpv(rate):
#         return sum(
#             cf / (1 + rate) ** ((d - first_date).days / 365)
#             for cf, d in zip(cash_flows, dates)
#         )

#     # Find the rate where XNPV = 0
#     return brentq(xnpv, -0.25, 0.25)


def _fund_table(rows_df):
    table = rows_df[["n_id", "invested", "current", "xirr", "pnl", "pnl_pct"]].copy()
    table.columns = ["Fund", "Invested", "Current", "XIRR", "PnL", "PnL %"]
    return table


def _format_delta(value):
    value = np.round(value, 2)
    if value > 0:
        return f"↑ {value}"
    elif value < 0:
        return f"↓ {abs(value)}"
    return f"— {value}"


def _style_green_red_old(value):
    if value > 0:
        return "background-color: #33d670; font-weight: 600"
    elif value < 0:
        return "background-color: #d13f3f; color:white; font-weight: 600"
    return ""

def _style_green_red_old_2(value):
    if "↑" in value:
        return "color: rgb(21, 130, 55); font-weight: 600"
    elif "↓" in value:
        return "color: #d13f3f; font-weight: 600"
    return ""


def _style_green_red(value):
    if "↑" in value:
        return """
            color: #21c354;
            background-color: rgba(33, 195, 84, 0.12);
            font-weight: 600;
            border-radius: 6px;
        """
    elif "↓" in value:
        return """
            color: #ff4b4b;
            background-color: rgba(255, 75, 75, 0.12);
            font-weight: 600;
            border-radius: 6px;
        """
    return ""


def _show_vendor_holdings(df, vendor):
    vendor_df = df[df["vendor"] == vendor]

    if vendor_df.empty:
        return

    st.subheader(f"{vendor} Mutual Fund")

    summary_cols = st.columns(5) #6

    invested = vendor_df["invested"].sum()
    current = vendor_df["current"].sum()
    total_pnl = current - invested

    tmp_delta = ((current - invested) / invested * 100) if invested else 0.0

    summary_cols[0].metric("Invested", fmt_inr(invested))
    summary_cols[1].metric("Current", fmt_inr(current))
    summary_cols[2].metric(
        "Overall PnL",
        fmt_inr(total_pnl),
        delta=fmt_pct(tmp_delta),
    )

    avg_xirr = vendor_df["xirr"].dropna().mean()
    summary_cols[3].metric(
        "Avg Fund XIRR",
        fmt_pct(avg_xirr) if pd.notna(avg_xirr) else "N/A",
    )

    dated = vendor_df.loc[
        vendor_df["date_parsed"].notna() &
        (vendor_df["invested"] > 0),
        ["date_parsed", "invested"],
    ]

    cashflows = [
        (row.date_parsed.date(), -float(row.invested))
        for row in dated.itertuples(index=False)
    ]

    if current > 0:
        cashflows.append((date.today(), float(current)))

    try:
        xirr_vendor = xirr(cashflows) * 100 if len(cashflows) > 1 else 0.0
    except (ArithmeticError, OverflowError, ZeroDivisionError, ValueError):
        xirr_vendor = 0.0

    summary_cols[4].metric("XIRR", fmt_pct(xirr_vendor))

    # try:
    #     custom_cash_flows = [amount for _, amount in cashflows]
    #     cashflow_dates = [cashflow_date for cashflow_date, _ in cashflows]
    #     xirr_vendor_custom = (
    #         xirr_custom(custom_cash_flows, cashflow_dates)
    #         if len(custom_cash_flows) > 1
    #         else 0.0
    #     ) * 100
    # except (ArithmeticError, OverflowError, ZeroDivisionError, ValueError):
    #     xirr_vendor_custom = 0.0

    # summary_cols[5].metric("XIRR Custom", fmt_pct(xirr_vendor_custom))

    st.caption("Returns are computed using the XIRR method.")

    for f_id, group in vendor_df.groupby("f_id", sort=False, dropna=False):
        st.markdown("#### " + str(f_id))

        aggregate = aggregate_by_fund(df, vendor, f_id)
        fund_table = _fund_table(aggregate)

        # Amount Columns
        for col in ["Invested", "Current"]:
            fund_table[col] = fund_table[col].astype(int)    
            fund_table[col] = fund_table[col].apply(lambda x : fmt_inr(x))

        # Arrow Addition
        for col in ["XIRR", "PnL", "PnL %"]:
            fund_table[col] = fund_table[col].map(_format_delta)

        # % Addition
        for col in ["XIRR","PnL %"]:
            fund_table[col] = fund_table[col].astype(str) + " %"
        
        st.dataframe(
            fund_table.style.apply(
                lambda column: column.map(_style_green_red),
                subset=["XIRR", "PnL", "PnL %"],
            ),
            hide_index=True,
            use_container_width=True,
        )


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
        