import streamlit as st

def inject_styles():

    st.markdown("""
    <style>
    html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"], .stApp { background: #f5f7f8 !important; color: #17212b !important; }
    [data-testid="stHeader"]            { background: transparent !important; }
    [data-testid="stSidebar"]           { display: none; }
    section.main > div                  { padding-top: 1.5rem; }
    [data-testid="stMetric"]            { background:#ffffff; border:1px solid #ccd6dc; border-radius:12px; padding:14px 18px; box-shadow:0 2px 8px rgba(30,55,70,.05); }
    [data-testid="stMetricLabel"] p     { color:#52606d !important; font-size:.7rem !important; font-family:'DM Mono',monospace !important; text-transform:uppercase; letter-spacing:.08em; }
    [data-testid="stMetricValue"]       { color:#17212b !important; font-family:'DM Mono',monospace !important; }
    [data-testid="stMetricDelta"]       { font-family:'DM Mono',monospace !important; font-size:.8rem !important; }
    [data-testid="stFileUploader"]      { background:#ffffff; border:1px dashed #9aaab5; border-radius:14px; padding:16px 20px; box-shadow:0 2px 8px rgba(30,55,70,.04); }
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploader"] [data-testid="stFileUploadDropzone"] { background:#ffffff !important; color:#334e68 !important; }
    [data-testid="stFileUploader"] button { background:#ffffff !important; color:#334e68 !important; border:1px solid #9aaab5 !important; }
    [data-testid="stFileUploader"] svg { color:#52606d !important; fill:currentColor; stroke:currentColor; }
    [data-testid="stFileUploader"] *    { color:#334e68 !important; }
    .stTabs [data-baseweb="tab-list"]   { background:#e8eef1; border-radius:12px; padding:4px; border:1px solid #ccd6dc; gap:3px; width:fit-content; }
    .stTabs [data-baseweb="tab"]        { background:transparent; border-radius:9px; color:#52606d; font-family:'Outfit',sans-serif; font-size:.85rem; padding:8px 26px; }
    .stTabs [aria-selected="true"]      { background:#ffffff !important; color:#17212b !important; box-shadow:0 1px 4px rgba(30,55,70,.12); }
    .stTabs [data-baseweb="tab-border"] { display:none; }
    .stTabs [data-baseweb="tab-panel"]  { padding-top: 24px; }
    hr                                  { border-color:#d7e0e5; margin: 16px 0; }
    h3                                  { font-family:'Outfit',sans-serif !important; font-size:1rem !important; font-weight:600 !important; color:#243b53 !important; letter-spacing:-.2px; margin-bottom:4px; }
    div[data-testid="stMarkdownContainer"] p { color:#334e68; }
    </style>
    """, unsafe_allow_html=True)


    st.markdown("""
        <style>
            .block-container {
                padding-top: 0rem;
                padding-bottom: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
        </style>
    """, unsafe_allow_html=True)