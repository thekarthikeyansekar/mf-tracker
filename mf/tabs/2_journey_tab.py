import streamlit as st


def render_journey_tab(df):
    journey = df[df["date_parsed"].notna()].copy()
    if journey.empty:
        st.info("No dated transactions available.")
        return

    journey = journey.rename(columns={"date_parsed": "Date", "invested": "Invested"})
    st.scatter_chart(
        journey,
        x="Date",
        y="Invested",
        color="vendor",
        size="Invested",
        use_container_width=True,
    )