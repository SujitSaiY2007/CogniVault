"""
CogniVault 2.0 Design System & Theme.
Premium Light Visual System (Track D Hackathon Quality).
"""
from __future__ import annotations

# Color Palette Tokens
BG_COLOR = "#F7F8FC"
SURFACE_COLOR = "#FFFFFF"
SURFACE_MUTED = "#F8FAFC"
SURFACE_HOVER = "#F1F5F9"

TEXT_PRIMARY = "#18233B"
TEXT_SECONDARY = "#68738A"
TEXT_MUTED = "#94A3B8"

BORDER_COLOR = "#E2E8F0"
BORDER_STRONG = "#CBD5E1"

ACCENT_INDIGO = "#4F46E5"
ACCENT_INDIGO_HOVER = "#4338CA"
ACCENT_INDIGO_LIGHT = "#EEF2FF"

ACCENT_TEAL = "#0D9488"
ACCENT_TEAL_LIGHT = "#F0FDFA"

SUCCESS_GREEN = "#16A34A"
SUCCESS_GREEN_LIGHT = "#F0FDF4"
SUCCESS_GREEN_BORDER = "#BBF7D0"

WARNING_AMBER = "#D97706"
WARNING_AMBER_LIGHT = "#FFFBEB"
WARNING_AMBER_BORDER = "#FDE68A"

DANGER_RED = "#DC2626"
DANGER_RED_LIGHT = "#FEF2F2"
DANGER_RED_BORDER = "#FECACA"

# Complete Responsive Streamlit CSS Theme Injection
THEME_CSS = f"""
<style>
    /* Global App Container */
    .stApp {{
        background-color: {BG_COLOR} !important;
        color: {TEXT_PRIMARY} !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        font-feature-settings: "cv02", "cv03", "cv04", "cv11";
    }}

    /* Global Headings — Prevents Single Letter Wrapping */
    h1, h2, h3, h4, h5, h6 {{
        color: {TEXT_PRIMARY} !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.015em !important;
        word-break: normal !important;
        overflow-wrap: break-word !important;
        white-space: normal !important;
    }}

    h1 {{ font-size: 1.75rem !important; margin-bottom: 0.5rem !important; }}
    h2 {{ font-size: 1.4rem !important; margin-top: 1.1rem !important; margin-bottom: 0.5rem !important; }}
    h3 {{ font-size: 1.18rem !important; margin-bottom: 0.35rem !important; }}
    h4 {{ font-size: 1.02rem !important; font-weight: 600 !important; }}

    /* Sidebar Shell — Minimal & Sleek */
    [data-testid="stSidebar"] {{
        background-color: {SURFACE_COLOR} !important;
        border-right: 1px solid {BORDER_COLOR} !important;
        box-shadow: 1px 0 3px rgba(0, 0, 0, 0.02) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        padding-top: 1.15rem;
        gap: 0.5rem;
    }}

    /* Sidebar Radio Navigation Items */
    [data-testid="stSidebar"] .stRadio > div {{
        gap: 0.25rem;
    }}

    [data-testid="stSidebar"] .stRadio label {{
        padding: 0.5rem 0.85rem !important;
        border-radius: 8px !important;
        font-size: 0.93rem !important;
        font-weight: 500 !important;
        color: {TEXT_PRIMARY} !important;
        transition: all 0.15s ease-in-out !important;
    }}

    [data-testid="stSidebar"] .stRadio label:hover {{
        background-color: {SURFACE_MUTED} !important;
        color: {ACCENT_INDIGO} !important;
    }}

    /* Main Container Cards */
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {{
        background-color: {SURFACE_COLOR} !important;
        border: 1px solid {BORDER_COLOR} !important;
        border-radius: 12px !important;
        padding: 1.35rem !important;
        margin-bottom: 1.15rem !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03), 0 1px 2px 0 rgba(0, 0, 0, 0.02) !important;
    }}

    /* Button System */
    .stButton > button[kind="primary"] {{
        background-color: {ACCENT_INDIGO} !important;
        border: 1px solid {ACCENT_INDIGO} !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.25rem !important;
        box-shadow: 0 1px 2px 0 rgba(79, 70, 229, 0.25) !important;
        transition: all 0.15s ease-in-out !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        background-color: {ACCENT_INDIGO_HOVER} !important;
        border-color: {ACCENT_INDIGO_HOVER} !important;
        box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.3) !important;
        transform: translateY(-1px);
    }}

    .stButton > button[kind="secondary"], .stButton > button:not([kind="primary"]) {{
        background-color: {SURFACE_COLOR} !important;
        border: 1px solid {BORDER_STRONG} !important;
        color: {TEXT_PRIMARY} !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        border-radius: 8px !important;
        padding: 0.45rem 1.15rem !important;
        transition: all 0.15s ease-in-out !important;
    }}

    .stButton > button[kind="secondary"]:hover, .stButton > button:not([kind="primary"]):hover {{
        background-color: {SURFACE_MUTED} !important;
        border-color: {ACCENT_INDIGO} !important;
        color: {ACCENT_INDIGO} !important;
    }}

    /* Metrics Styling */
    [data-testid="stMetric"] {{
        background-color: {SURFACE_COLOR} !important;
        border: 1px solid {BORDER_COLOR} !important;
        border-radius: 10px !important;
        padding: 1rem 1.25rem !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
    }}

    [data-testid="stMetricValue"] {{
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        color: {TEXT_PRIMARY} !important;
        line-height: 1.2 !important;
    }}

    [data-testid="stMetricLabel"] {{
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: {TEXT_SECONDARY} !important;
        text-transform: uppercase !important;
        letter-spacing: 0.03em !important;
    }}

    /* Input Fields & Select Boxes */
    .stTextInput > div > div > input, .stSelectbox > div > div {{
        background-color: {SURFACE_COLOR} !important;
        border: 1px solid {BORDER_STRONG} !important;
        border-radius: 8px !important;
        color: {TEXT_PRIMARY} !important;
        font-size: 0.95rem !important;
    }}

    .stTextInput > div > div > input:focus {{
        border-color: {ACCENT_INDIGO} !important;
        box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.15) !important;
    }}

    /* Expanders */
    [data-testid="stExpander"] {{
        border: 1px solid {BORDER_COLOR} !important;
        border-radius: 10px !important;
        background-color: {SURFACE_COLOR} !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
        margin-bottom: 0.75rem !important;
    }}

    /* Alerts and Banners */
    .stAlert {{
        border-radius: 10px !important;
        border-width: 1px !important;
    }}

    /* Dividers */
    hr {{
        border-color: {BORDER_COLOR} !important;
        margin: 1.25rem 0 !important;
    }}

    /* Dataframes */
    [data-testid="stDataFrame"] {{
        border: 1px solid {BORDER_COLOR} !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }}

    /* Custom Component Classes */
    .cogni-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        white-space: nowrap;
    }}

    .cogni-badge-indigo {{
        background-color: {ACCENT_INDIGO_LIGHT};
        color: {ACCENT_INDIGO};
        border: 1px solid #C7D2FE;
    }}

    .cogni-badge-teal {{
        background-color: {ACCENT_TEAL_LIGHT};
        color: {ACCENT_TEAL};
        border: 1px solid #99F6E4;
    }}

    .cogni-badge-success {{
        background-color: {SUCCESS_GREEN_LIGHT};
        color: {SUCCESS_GREEN};
        border: 1px solid {SUCCESS_GREEN_BORDER};
    }}

    .cogni-badge-warning {{
        background-color: {WARNING_AMBER_LIGHT};
        color: {WARNING_AMBER};
        border: 1px solid {WARNING_AMBER_BORDER};
    }}

    .cogni-badge-danger {{
        background-color: {DANGER_RED_LIGHT};
        color: {DANGER_RED};
        border: 1px solid {DANGER_RED_BORDER};
    }}

    .cogni-badge-neutral {{
        background-color: {SURFACE_MUTED};
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER_COLOR};
    }}

    .hero-card {{
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid {BORDER_COLOR};
        border-radius: 14px;
        padding: 1.75rem 2rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
    }}

    .card-title {{
        font-size: 1.25rem;
        font-weight: 700;
        color: {TEXT_PRIMARY};
        margin-bottom: 0.35rem;
    }}

    .card-subtitle {{
        font-size: 0.92rem;
        color: {TEXT_SECONDARY};
        line-height: 1.5;
    }}

    .citation-card {{
        background-color: #FAFAFD;
        border: 1px solid {BORDER_COLOR};
        border-left: 4px solid {ACCENT_INDIGO};
        border-radius: 8px;
        padding: 0.9rem 1.15rem;
        margin-top: 0.65rem;
        margin-bottom: 0.65rem;
    }}

    .onboarding-banner {{
        background: linear-gradient(135deg, #EEF2FF 0%, #F0FDFA 100%);
        border: 1px solid #C7D2FE;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-top: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
    }}

    /* Dashboard Header & Section Components */
    .dashboard-header-box {{
        background: #FFFFFF;
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
        padding: 0.65rem 1rem;
        margin-bottom: 1.15rem;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
    }}

    .quick-action-card {{
        background: #FFFFFF;
        border: 1px solid {BORDER_COLOR};
        border-radius: 10px;
        padding: 1.15rem 1rem;
        text-align: left;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        height: 100%;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
    }}
    .quick-action-card:hover {{
        border-color: {ACCENT_INDIGO};
        transform: translateY(-2px);
        box-shadow: 0 6px 12px -2px rgba(79, 70, 229, 0.08);
    }}

    .history-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 0.5rem;
        border-bottom: 1px solid {BORDER_COLOR};
        font-size: 0.88rem;
    }}
    .history-row:last-child {{
        border-bottom: none;
    }}

    .resume-badge {{
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: {ACCENT_INDIGO};
        background: {ACCENT_INDIGO_LIGHT};
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
    }}
</style>
"""
