import streamlit as st
from utils.helpers import *
from custom_styles import inject_styles

from nps.renderer import render_nps_tab
from nps.loader import load_nps_data

from mf.loader import load_mf_data
from mf.renderer import render_mf_tab

st.set_page_config(
    page_title="Portfolio Tracker",
    page_icon="📈",
    layout="wide",
)
# inject_styles()

st.title("Portfolio Tracker")

st.markdown('<style>' + open('./custom_styles/tab.css').read() + '</style>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION + UPLOADS
# ══════════════════════════════════════════════════════════════════════════
page = st.sidebar.radio(
    "Portfolio",
    ["📊  Mutual Funds", "🏛️  NPS"],
    index=0,
    key="portfolio_page",
)

mf_file = st.sidebar.file_uploader(
    "Upload MF Tracker CSV",
    type=["csv"], key="mf_upload",
    help="Expected columns: Vendor, Active, N Identifier, AMFI Scheme Code, F Identifier, Date, Invested Amount, Current Amount, Profit, Absolute Profit %, XIRR. Optional: NAV",
)

nps_file = st.sidebar.file_uploader(
    "Upload NPS Tracker CSV",
    type=["csv"], key="nps_upload",
    help="Expected columns: Year, Category, Fund Name, Date, Particulars, Amount, NAV, Units",
)

# Keep the last parsed content for each section across page switches.
if "mf_df" not in st.session_state:
    st.session_state.mf_df = None
if "mf_file_token" not in st.session_state:
    st.session_state.mf_file_token = None

if "nps_df" not in st.session_state:
    st.session_state.nps_df = None
if "nps_file_token" not in st.session_state:
    st.session_state.nps_file_token = None

# ── MF section ─────────────────────────────────────────────────────────────────
if page == "📊  Mutual Funds":
    if mf_file is not None:
        mf_token = f"{mf_file.name}:{mf_file.size}:{mf_file.type}"
        if st.session_state.mf_file_token != mf_token:
            try:
                st.session_state.mf_df = load_mf_data(mf_file)
                st.session_state.mf_file_token = mf_token
            except Exception as e:
                st.error(f"Could not parse MF CSV: {e}")
                st.exception(e)

        mf_df = st.session_state.mf_df
        if mf_df is not None and mf_df.empty:
            st.warning("No active Axis/DSP holdings found. Check Vendor names and Active column.")
        elif mf_df is not None:
            render_mf_tab(mf_df)
        else:
            st.info("Upload a CSV above to view your Mutual Fund holdings and investment journey.")
    elif st.session_state.mf_df is not None:
        if st.session_state.mf_df.empty:
            st.warning("No active Axis/DSP holdings found. Check Vendor names and Active column.")
        else:
            render_mf_tab(st.session_state.mf_df)
    else:
        st.info("Upload a CSV above to view your Mutual Fund holdings and investment journey.")

# ── NPS section ────────────────────────────────────────────────────────────────
elif page == "🏛️  NPS":
    if nps_file is not None:
        nps_token = f"{nps_file.name}:{nps_file.size}:{nps_file.type}"
        if st.session_state.nps_file_token != nps_token:
            try:
                st.session_state.nps_df = load_nps_data(nps_file)
                st.session_state.nps_file_token = nps_token
            except Exception as e:
                st.error(f"Could not parse NPS CSV: {e}")
                st.exception(e)

        nps_df = st.session_state.nps_df
        if nps_df is not None and nps_df.empty:
            st.warning("No valid NPS rows found. Check Date format and Amount column.")
        elif nps_df is not None:
            render_nps_tab(nps_df)
        else:
            st.info("Upload a CSV above to view your NPS investment charts.")
    elif st.session_state.nps_df is not None:
        if st.session_state.nps_df.empty:
            st.warning("No valid NPS rows found. Check Date format and Amount column.")
        else:
            render_nps_tab(st.session_state.nps_df)
    else:
        st.info("Upload a CSV above to view your NPS investment charts.")