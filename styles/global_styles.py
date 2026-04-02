import streamlit as st

def inject_styles():

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