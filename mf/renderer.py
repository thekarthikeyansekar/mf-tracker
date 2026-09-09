import streamlit as st
from datetime import datetime

from mf.tabs import render_holdings_tab, render_journey_tab, render_tracker_tab
from mf.utils.mf_price_retreiver import get_today_mf_prices
from mf.utils.nav_advsior import analyze_nav_advisor, write_nav_advisor_csv


def render_mf_tab(df):
    col_1, col_2, _ = st.columns([1,1,6])
    with col_1:
        if st.button("Run NAV Advisor Analysis", type="primary"):
            advisor_df = analyze_nav_advisor(df)
            output_path = write_nav_advisor_csv(advisor_df)
            st.success(f"Analysis saved to {output_path.name}.")
            st.download_button(
                "Download NAV advisor CSV",
                data=advisor_df.to_csv(index=False),
                file_name=output_path.name,
                mime="text/csv",
            )
    with col_2:
        if st.button("Refresh MF prices", type="secondary"):
            prices_path = get_today_mf_prices()
            st.success(f"MF prices refreshed at {prices_path}")
            st.rerun()

    # Here
    holdings_tab, journey_tab, tracker_tab = st.tabs(
            ["Holdings", "Investment Journey", "Fund-wise Tracker"]
        )

    with holdings_tab:
        df["delta_date"] = (datetime.now() - df["date_parsed"]).dt.days
        render_holdings_tab(df)

    with journey_tab:
        render_journey_tab(df)

    with tracker_tab:
        render_tracker_tab(df)
    