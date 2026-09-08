import streamlit as st

def inject_styles():
    st.html(
        """
        <style>

        /* =========================================================
           GLOBAL
           ========================================================= */

        :root {
            --table-border: #cbd5df;
            --table-header: #eef2f5;
            --table-header-text: #526174;
            --table-row-hover: #f7fafc;
            --table-text: #102a43;

            --tab-bg: #ffffff;
            --tab-active: #e8edf2;
            --tab-text: #526174;
            --tab-border: #d5dce3;
        }


        /* =========================================================
           DATAFRAME CONTAINER
           ========================================================= */

        [data-testid="stDataFrame"] {
            width: 100% !important;
            max-width: 100% !important;

            border: 1px solid var(--table-border) !important;
            border-radius: 16px !important;

            overflow: hidden !important;

            background: #ffffff !important;

            box-shadow:
                0 1px 2px rgba(16, 42, 67, 0.04) !important;
        }


        [data-testid="stDataFrame"] > div {
            border: none !important;
        }


        /* =========================================================
           GLIDE DATA GRID
           ========================================================= */

        [data-testid="stDataFrame"] canvas {
            outline: none !important;
        }


        /* =========================================================
           HEADER
           ========================================================= */

        [data-testid="stDataFrame"] [role="columnheader"],
        [data-testid="stDataFrame"] .gdg-header,
        [data-testid="stDataFrame"] [class*="header"] {

            background-color: var(--table-header) !important;

            color: var(--table-header-text) !important;

            font-weight: 800 !important;

            font-size: 12px !important;

            letter-spacing: 0.06em !important;

            text-transform: uppercase !important;

            white-space: normal !important;

            overflow-wrap: anywhere !important;

            word-break: break-word !important;

            line-height: 1.25 !important;
        }


        /* Header text */

        [data-testid="stDataFrame"] [role="columnheader"] *,
        [data-testid="stDataFrame"] .gdg-header *,
        [data-testid="stDataFrame"] [class*="header"] * {

            color: var(--table-header-text) !important;

            font-weight: 800 !important;

            text-transform: uppercase !important;

            white-space: normal !important;

            overflow-wrap: anywhere !important;

            word-break: break-word !important;
        }


        /* =========================================================
           TABLE CELLS
           ========================================================= */

        [data-testid="stDataFrame"] [role="gridcell"] {

            color: var(--table-text) !important;

            font-size: 14px !important;

            line-height: 1.35 !important;

            white-space: normal !important;

            overflow-wrap: anywhere !important;

            word-break: break-word !important;

            border-color: var(--table-border) !important;
        }


        [data-testid="stDataFrame"] [role="gridcell"] * {

            white-space: normal !important;

            overflow-wrap: anywhere !important;

            word-break: break-word !important;
        }


        /* Row hover */

        [data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {

            background-color: var(--table-row-hover) !important;
        }


        /* =========================================================
           TABS — PILL / SEGMENTED STYLE
           ========================================================= */

        .stTabs {
            width: 100% !important;
        }


        /* Remove bullets */

        .stTabs ul,
        .stTabs ol,
        .stTabs li {

            list-style: none !important;

            margin: 0 !important;

            padding: 0 !important;
        }


        /* Tab list */

        .stTabs [data-baseweb="tab-list"] {

            display: flex !important;

            align-items: stretch !important;

            width: 100% !important;

            gap: 4px !important;

            padding: 4px !important;

            background: var(--tab-bg) !important;

            border: 1px solid var(--tab-border) !important;

            border-radius: 12px !important;

            box-sizing: border-box !important;

            overflow-x: auto !important;

            scrollbar-width: none !important;
        }


        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
            display: none !important;
        }


        /* Individual tabs */

        .stTabs [data-baseweb="tab"] {

            display: flex !important;

            align-items: center !important;

            justify-content: center !important;

            flex: 1 1 0 !important;

            min-width: 0 !important;

            min-height: 42px !important;

            padding: 7px 16px !important;

            margin: 0 !important;

            border: none !important;

            border-radius: 10px !important;

            background: transparent !important;

            color: var(--tab-text) !important;

            font-size: 13px !important;

            font-weight: 650 !important;

            line-height: 1.2 !important;

            text-align: center !important;

            white-space: normal !important;

            overflow-wrap: anywhere !important;

            word-break: break-word !important;

            box-sizing: border-box !important;

            transition:
                background 0.15s ease,
                color 0.15s ease,
                box-shadow 0.15s ease !important;
        }


        /* Remove Streamlit underline */

        .stTabs [data-baseweb="tab"]::after,
        .stTabs [data-baseweb="tab"]::before,
        .stTabs [data-baseweb="tab-highlight"] {

            display: none !important;

            content: none !important;

            height: 0 !important;

            background: transparent !important;
        }


        /* Active tab */

        .stTabs [data-baseweb="tab"][aria-selected="true"] {

            background: var(--tab-active) !important;

            color: #344454 !important;

            box-shadow:
                0 1px 3px rgba(16, 42, 67, 0.12),
                inset 0 0 0 1px rgba(16, 42, 67, 0.04) !important;
        }


        /* Hover */

        .stTabs [data-baseweb="tab"]:hover {

            background: #f4f6f8 !important;

            color: #263746 !important;
        }


        .stTabs [data-baseweb="tab"][aria-selected="true"]:hover {

            background: var(--tab-active) !important;
        }


        /* Tab text */

        .stTabs [data-baseweb="tab"] p,
        .stTabs [data-baseweb="tab"] span {

            margin: 0 !important;

            padding: 0 !important;

            color: inherit !important;

            font-size: inherit !important;

            font-weight: inherit !important;

            line-height: inherit !important;

            text-align: center !important;

            white-space: normal !important;

            overflow-wrap: anywhere !important;

            word-break: break-word !important;
        }


        /* =========================================================
           TABLET
           ========================================================= */

        @media (max-width: 768px) {

            [data-testid="stDataFrame"] {

                border-radius: 12px !important;
            }


            [data-testid="stDataFrame"] [role="columnheader"],
            [data-testid="stDataFrame"] .gdg-header {

                font-size: 11px !important;

                font-weight: 800 !important;

                white-space: normal !important;

                overflow-wrap: anywhere !important;

                word-break: break-word !important;
            }


            [data-testid="stDataFrame"] [role="gridcell"] {

                font-size: 13px !important;

                white-space: normal !important;

                overflow-wrap: anywhere !important;

                word-break: break-word !important;
            }


            .stTabs [data-baseweb="tab-list"] {

                border-radius: 11px !important;
            }


            .stTabs [data-baseweb="tab"] {

                min-height: 44px !important;

                padding: 7px 10px !important;

                font-size: 12px !important;
            }
        }


        /* =========================================================
           MOBILE
           ========================================================= */

        @media (max-width: 480px) {

            [data-testid="stDataFrame"] {

                border-radius: 10px !important;
            }


            [data-testid="stDataFrame"] [role="columnheader"],
            [data-testid="stDataFrame"] .gdg-header {

                font-size: 10px !important;

                font-weight: 800 !important;

                letter-spacing: 0.04em !important;

                line-height: 1.2 !important;

                white-space: normal !important;

                overflow-wrap: anywhere !important;

                word-break: break-word !important;
            }


            [data-testid="stDataFrame"] [role="gridcell"] {

                font-size: 12px !important;

                line-height: 1.25 !important;

                white-space: normal !important;

                overflow-wrap: anywhere !important;

                word-break: break-word !important;
            }


            [data-testid="stDataFrame"] [role="gridcell"] * {

                white-space: normal !important;

                overflow-wrap: anywhere !important;

                word-break: break-word !important;
            }


            /* Mobile tabs */

            .stTabs [data-baseweb="tab-list"] {

                gap: 3px !important;

                padding: 3px !important;

                border-radius: 10px !important;
            }


            .stTabs [data-baseweb="tab"] {

                min-width: 0 !important;

                min-height: 42px !important;

                padding: 6px 7px !important;

                font-size: 11px !important;

                font-weight: 650 !important;

                line-height: 1.15 !important;

                white-space: normal !important;

                overflow-wrap: anywhere !important;

                word-break: break-word !important;
            }


            .stTabs [data-baseweb="tab"] p,
            .stTabs [data-baseweb="tab"] span {

                white-space: normal !important;

                overflow-wrap: anywhere !important;

                word-break: break-word !important;
            }
        }

        </style>
        """
    )