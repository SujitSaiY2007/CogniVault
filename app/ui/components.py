"""
CogniVault 2.0 Reusable UI Components.
Modular visual component renderers for Streamlit.
All components are formatted without leading line indentation to prevent
CommonMark markdown parsers from treating HTML tags as indented code blocks.
"""
from __future__ import annotations

import textwrap
import streamlit as st


def _render_html_fragment(fragment: str) -> None:
    """Render a self-contained HTML fragment without CommonMark blank-line breaks.

    Streamlit's Markdown parser can terminate an HTML block at a blank line and
    expose subsequent tags as literal text. Keep the markup contiguous and
    never use this helper for fragments spanning separate Streamlit elements.
    """
    compact = "\n".join(line for line in fragment.splitlines() if line.strip())
    st.markdown(compact, unsafe_allow_html=True)


from app.ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BORDER_COLOR, ACCENT_INDIGO, ACCENT_TEAL,
    SUCCESS_GREEN, WARNING_AMBER, DANGER_RED
)


def render_page_header(
    title: str,
    description: str,
    badge_text: str | None = None,
    badge_variant: str = "indigo"
) -> None:
    """Renders a standard, premium page header across all modules."""
    badge_html = f'<span class="cogni-badge cogni-badge-{badge_variant}" style="margin-left: 0.65rem; vertical-align: middle;">{badge_text}</span>' if badge_text else ""

    html = textwrap.dedent(f"""
<div style="margin-bottom: 1.25rem; padding-bottom: 0.85rem; border-bottom: 1px solid {BORDER_COLOR};">
<div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
<div style="display: flex; align-items: center; flex-wrap: wrap;">
<h1 style="margin: 0; font-size: 1.75rem; font-weight: 700; color: {TEXT_PRIMARY}; display: inline; white-space: normal; word-break: normal;">{title}</h1>{badge_html}
</div>
</div>
<div style="margin: 0.35rem 0 0 0; font-size: 0.94rem; color: {TEXT_SECONDARY}; line-height: 1.5;">{description}</div>
</div>
""").strip()
    _render_html_fragment(html)


def render_section_header(title: str, subtitle: str | None = None, badge_text: str | None = None) -> None:
    """Renders a section header with optional subtitle and badge, free of raw HTML leakage."""
    badge_html = f'<span class="cogni-badge cogni-badge-neutral" style="margin-left: 0.5rem; vertical-align: middle;">{badge_text}</span>' if badge_text else ""
    sub_html = f'<div style="margin: 0.2rem 0 0.75rem 0; font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.4;">{subtitle}</div>' if subtitle else '<div style="margin-bottom: 0.45rem;"></div>'

    html = textwrap.dedent(f"""
<div style="margin-top: 1.15rem; margin-bottom: 0.35rem;">
<div style="display: flex; align-items: center; flex-wrap: wrap; gap: 0.4rem;">
<h3 style="margin: 0; font-size: 1.18rem; font-weight: 700; color: {TEXT_PRIMARY}; white-space: normal; word-break: normal;">{title}</h3>{badge_html}
</div>
{sub_html}
</div>
""").strip()
    _render_html_fragment(html)


def render_metric_card(
    label: str,
    value: str | int | float,
    subtext: str | None = None,
    badge: str | None = None,
    badge_variant: str = "indigo"
) -> None:
    """Renders an aesthetic, structured KPI metric card."""
    badge_html = f'<span class="cogni-badge cogni-badge-{badge_variant}" style="font-size: 0.72rem; padding: 0.15rem 0.5rem;">{badge}</span>' if badge else ""
    subtext_html = f'<div style="font-size: 0.82rem; color: {TEXT_SECONDARY}; margin-top: 0.3rem; line-height: 1.3;">{subtext}</div>' if subtext else ""

    html = textwrap.dedent(f"""
<div style="background: #FFFFFF; border: 1px solid {BORDER_COLOR}; border-radius: 10px; padding: 1rem 1.15rem; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03); display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.35rem;">
<span style="font-size: 0.82rem; font-weight: 600; color: {TEXT_SECONDARY}; text-transform: uppercase; letter-spacing: 0.03em;">{label}</span>{badge_html}
</div>
<div style="font-size: 1.65rem; font-weight: 700; color: {TEXT_PRIMARY}; line-height: 1.2;">{value}</div>
{subtext_html}
</div>
""").strip()
    st.markdown(html, unsafe_allow_html=True)


def render_badge(text: str, variant: str = "indigo") -> str:
    """Returns HTML for an inline tag badge."""
    return f'<span class="cogni-badge cogni-badge-{variant}">{text}</span>'


def render_callout(
    title: str,
    message: str,
    variant: str = "indigo",
    icon: str | None = None
) -> None:
    """Renders a styled callout box with accent border."""
    border_map = {
        "indigo": ACCENT_INDIGO,
        "teal": ACCENT_TEAL,
        "success": SUCCESS_GREEN,
        "warning": WARNING_AMBER,
        "danger": DANGER_RED,
        "neutral": BORDER_COLOR
    }
    bg_map = {
        "indigo": "#EEF2FF",
        "teal": "#F0FDFA",
        "success": "#F0FDF4",
        "warning": "#FFFBEB",
        "danger": "#FEF2F2",
        "neutral": "#F8FAFC"
    }
    border_color = border_map.get(variant, ACCENT_INDIGO)
    bg_color = bg_map.get(variant, "#EEF2FF")
    icon_str = f"{icon} " if icon else ""

    html = textwrap.dedent(f"""
<div style="background-color: {bg_color}; border: 1px solid {border_color}40; border-left: 4px solid {border_color}; border-radius: 8px; padding: 0.85rem 1.15rem; margin-bottom: 0.85rem;">
<div style="font-weight: 600; font-size: 0.94rem; color: {TEXT_PRIMARY}; margin-bottom: 0.2rem;">{icon_str}{title}</div>
<div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.45;">{message}</div>
</div>
""").strip()
    st.markdown(html, unsafe_allow_html=True)


def render_empty_state(title: str, description: str, icon: str = "📂") -> None:
    """Renders a friendly, clean empty state container."""
    html = textwrap.dedent(f"""
<div style="text-align: center; padding: 2.25rem 1.25rem; background: #FFFFFF; border: 1px dashed {BORDER_COLOR}; border-radius: 12px; margin: 1.15rem 0;">
<div style="font-size: 2.2rem; margin-bottom: 0.45rem;">{icon}</div>
<div style="font-size: 1.05rem; font-weight: 600; color: {TEXT_PRIMARY}; margin-bottom: 0.25rem;">{title}</div>
<div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; max-width: 460px; margin: 0 auto; line-height: 1.45;">{description}</div>
</div>
""").strip()
    st.markdown(html, unsafe_allow_html=True)


def render_citation_card(
    index: int,
    evidence_id: str,
    source_title: str,
    modality: str,
    locator_str: str,
    snippet: str,
    source_path: str | None = None
) -> None:
    """Renders an evidence citation card with locator badges."""
    source_info = f'<div style="color: {TEXT_MUTED}; font-size: 0.78rem; margin-top: 0.35rem;">Source: {source_path}</div>' if source_path else ""

    html = textwrap.dedent(f"""
<div class="citation-card">
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.45rem; flex-wrap: wrap; gap: 0.4rem;">
<div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
<span style="font-weight: 700; color: {ACCENT_INDIGO}; font-size: 0.92rem;">[{index}] Evidence <code style="color: {ACCENT_INDIGO};">{evidence_id}</code></span>
<span class="cogni-badge cogni-badge-neutral">{modality.upper()}</span>
<span class="cogni-badge cogni-badge-indigo">{locator_str}</span>
</div>
<span style="font-size: 0.85rem; font-weight: 500; color: {TEXT_PRIMARY};">{source_title}</span>
</div>
<div style="font-size: 0.9rem; color: {TEXT_PRIMARY}; background: #FFFFFF; border: 1px solid {BORDER_COLOR}; border-radius: 6px; padding: 0.65rem 0.85rem; font-style: italic; line-height: 1.45;">
"{snippet}"
</div>
{source_info}
</div>
""").strip()
    st.markdown(html, unsafe_allow_html=True)
