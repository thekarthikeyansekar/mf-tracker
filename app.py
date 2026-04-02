import streamlit as st
import numpy as np
import pandas as pd
import json
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.helpers import *
from styles.global_styles import inject_styles

from nps.renderer import render_nps_tab
from nps.loader import load_nps_data

from mf.loader import load_mf_data
from mf.renderer import render_mf_tab


st.set_page_config(
    page_title="Portfolio Tracker",
    page_icon="📈",
    layout="wide",
)

inject_styles()

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
            # st.dataframe(nps_df)
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