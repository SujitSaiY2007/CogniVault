"""CogniVault design tokens and responsive visual system."""
from __future__ import annotations

# Warm, quiet surfaces with a restrained indigo/teal accent system.
BG_COLOR = "#F6F7FB"
SURFACE_COLOR = "#FFFFFF"
SURFACE_MUTED = "#F8FAFC"
SURFACE_HOVER = "#EEF2FF"
TEXT_PRIMARY = "#172033"
TEXT_SECONDARY = "#596579"
TEXT_MUTED = "#8490A3"
BORDER_COLOR = "#E3E7EF"
BORDER_STRONG = "#CBD3E1"
ACCENT_INDIGO = "#4F46E5"
ACCENT_INDIGO_HOVER = "#4338CA"
ACCENT_INDIGO_LIGHT = "#EEF2FF"
ACCENT_TEAL = "#0F8B83"
ACCENT_TEAL_LIGHT = "#EAF8F6"
SUCCESS_GREEN = "#15803D"
SUCCESS_GREEN_LIGHT = "#F0FDF4"
SUCCESS_GREEN_BORDER = "#BBF7D0"
WARNING_AMBER = "#B45309"
WARNING_AMBER_LIGHT = "#FFFBEB"
WARNING_AMBER_BORDER = "#FDE68A"
DANGER_RED = "#B91C1C"
DANGER_RED_LIGHT = "#FEF2F2"
DANGER_RED_BORDER = "#FECACA"

THEME_CSS = f"""
<style>
:root {{
  color-scheme: light;
  --cv-bg: {BG_COLOR};
  --cv-surface: {SURFACE_COLOR};
  --cv-text: {TEXT_PRIMARY};
  --cv-muted: {TEXT_SECONDARY};
  --cv-border: {BORDER_COLOR};
  --cv-accent: {ACCENT_INDIGO};
}}
html, body, [class*="css"] {{
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
.stApp {{
  background: var(--cv-bg);
  color: var(--cv-text);
}}
header[data-testid="stHeader"] {{
  background: transparent;
}}
[data-testid="stAppViewBlockContainer"] {{
  max-width: 1440px;
  padding-top: 1.35rem;
  padding-bottom: 2.5rem;
}}
[data-testid="stMainBlockContainer"] {{
  max-width: 1440px;
  padding-top: 1.35rem;
  padding-bottom: 2.5rem;
}}
[data-testid="stSidebar"] {{
  background: var(--cv-surface);
  border-right: 1px solid var(--cv-border);
}}
[data-testid="stSidebar"] > div:first-child {{
  padding-top: 1.2rem;
}}
.cv-brand {{
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: .25rem .2rem 1.15rem;
  margin-bottom: .75rem;
  border-bottom: 1px solid var(--cv-border);
}}
.cv-brand-mark {{
  display: grid;
  place-items: center;
  width: 2.45rem;
  height: 2.45rem;
  border-radius: .8rem;
  background: {ACCENT_INDIGO};
  color: white;
  font-size: 1.25rem;
  font-weight: 800;
}}
.cv-brand-name {{
  color: var(--cv-text);
  font-size: 1.15rem;
  font-weight: 760;
  letter-spacing: -.03em;
  line-height: 1.2;
}}
.cv-brand-caption {{
  color: var(--cv-muted);
  font-size: .76rem;
  margin-top: .15rem;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
  font-size: .86rem;
  line-height: 1.5;
}}
[data-testid="stSidebar"] .stRadio > div {{
  gap: .18rem;
}}
[data-testid="stSidebar"] .stRadio label {{
  padding: .45rem .6rem;
  border-radius: .65rem;
  font-size: .92rem;
}}
[data-testid="stSidebar"] .stRadio label:hover {{
  background: {SURFACE_MUTED};
}}
h1, h2, h3, h4 {{
  color: var(--cv-text);
  letter-spacing: -.035em;
  line-height: 1.22;
  overflow-wrap: break-word;
  word-break: normal;
}}
h1 {{ font-size: clamp(1.8rem, 2.6vw, 2.45rem); font-weight: 760; }}
h2 {{ font-size: clamp(1.35rem, 1.9vw, 1.7rem); font-weight: 720; }}
h3 {{ font-size: 1.12rem; font-weight: 680; }}
p, li {{
  color: var(--cv-muted);
  line-height: 1.65;
}}
[data-testid="stVerticalBlock"] {{
  min-width: 0;
}}
[data-testid="stHorizontalBlock"] {{
  gap: 1rem;
}}
[data-testid="column"] {{
  min-width: 0 !important;
}}
[data-testid="stContainer"] {{
  border-color: var(--cv-border);
  border-radius: 1rem;
}}
div[data-testid="stVerticalBlockBorderWrapper"] {{
  background: var(--cv-surface);
  border-color: var(--cv-border);
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(23, 32, 51, .025);
}}
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {{
  border-radius: .7rem;
  min-height: 2.55rem;
  font-weight: 620;
  transition: border-color .15s ease, background .15s ease, transform .15s ease;
}}
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {{
  background: {ACCENT_INDIGO};
  border: 1px solid {ACCENT_INDIGO};
  color: #fff;
}}
.stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {{
  background: {ACCENT_INDIGO_HOVER};
  border-color: {ACCENT_INDIGO_HOVER};
}}
.stButton > button:not([kind="primary"]), .stDownloadButton > button {{
  border-color: var(--cv-border);
  background: white;
  color: var(--cv-text);
}}
.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"], .stNumberInput input {{
  border-radius: .7rem;
  border-color: var(--cv-border);
}}
[data-testid="stMetric"] {{
  background: white;
  border: 1px solid var(--cv-border);
  border-radius: .9rem;
  padding: 1rem 1.1rem;
}}
[data-testid="stMetricLabel"] {{
  color: var(--cv-muted);
  font-size: .8rem;
  font-weight: 650;
}}
[data-testid="stMetricValue"] {{
  color: var(--cv-text);
  font-weight: 750;
}}
[data-testid="stExpander"] {{
  border: 1px solid var(--cv-border);
  border-radius: .85rem;
  background: white;
}}
.stAlert {{
  border-radius: .8rem;
}}
hr {{
  border-color: var(--cv-border);
}}
[data-testid="stDataFrame"], [data-testid="stTable"] {{
  border: 1px solid var(--cv-border);
  border-radius: .8rem;
  overflow: hidden;
}}
.cogni-badge {{
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  padding: .22rem .6rem;
  border-radius: 999px;
  font-size: .76rem;
  font-weight: 650;
  white-space: normal;
}}
.cogni-badge-indigo {{ background: {ACCENT_INDIGO_LIGHT}; color: {ACCENT_INDIGO}; border: 1px solid #C7D2FE; }}
.cogni-badge-teal {{ background: {ACCENT_TEAL_LIGHT}; color: {ACCENT_TEAL}; border: 1px solid #99F6E4; }}
.cogni-badge-success {{ background: {SUCCESS_GREEN_LIGHT}; color: {SUCCESS_GREEN}; border: 1px solid {SUCCESS_GREEN_BORDER}; }}
.cogni-badge-warning {{ background: {WARNING_AMBER_LIGHT}; color: {WARNING_AMBER}; border: 1px solid {WARNING_AMBER_BORDER}; }}
.cogni-badge-danger {{ background: {DANGER_RED_LIGHT}; color: {DANGER_RED}; border: 1px solid {DANGER_RED_BORDER}; }}
.cogni-badge-neutral {{ background: {SURFACE_MUTED}; color: {TEXT_SECONDARY}; border: 1px solid {BORDER_COLOR}; }}
.hero-card {{
  background: linear-gradient(135deg, #FFFFFF 0%, #F2F5FF 100%);
  border: 1px solid var(--cv-border);
  border-radius: 1.15rem;
  padding: clamp(1.25rem, 2.4vw, 2rem);
  box-shadow: 0 8px 28px rgba(23, 32, 51, .04);
}}
.card-title {{ color: var(--cv-text); font-size: 1.3rem; font-weight: 750; }}
.card-subtitle {{ color: var(--cv-muted); line-height: 1.6; }}
.citation-card {{
  background: white;
  border: 1px solid var(--cv-border);
  border-left: 3px solid {ACCENT_INDIGO};
  border-radius: .8rem;
  padding: .9rem 1rem;
  margin: .6rem 0;
}}
.quick-action-card {{
  background: white;
  border: 1px solid var(--cv-border);
  border-radius: .85rem;
  padding: .85rem;
}}
@media (max-width: 900px) {{
  [data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"] {{
    padding-left: 1rem;
    padding-right: 1rem;
  }}
}}
</style>
"""
