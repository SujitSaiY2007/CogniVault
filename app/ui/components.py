"""
CogniVault 2.0 Reusable UI Components.
Modular visual component renderers for Streamlit.
"""
from __future__ import annotations

import streamlit as st
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
    badge_html = ""
    if badge_text:
        badge_html = f'<span class="cogni-badge cogni-badge-{badge_variant}" style="margin-left: 0.75rem; vertical-align: middle;">{badge_text}</span>'

    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid {BORDER_COLOR};">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center;">
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 700; color: {TEXT_PRIMARY}; display: inline;">{title}</h1>
                    {badge_html}
                </div>
            </div>
            <p style="margin: 0.4rem 0 0 0; font-size: 0.96rem; color: {TEXT_SECONDARY}; line-height: 1.5;">{description}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_section_header(title: str, subtitle: str | None = None, badge_text: str | None = None) -> None:
    """Renders a section header with optional subtitle and badge."""
    badge_html = f'<span class="cogni-badge cogni-badge-neutral" style="margin-left: 0.5rem;">{badge_text}</span>' if badge_text else ""
    sub_html = f'<p style="margin: 0.15rem 0 0.85rem 0; font-size: 0.88rem; color: {TEXT_SECONDARY};">{subtitle}</p>' if subtitle else '<div style="margin-bottom: 0.75rem;"></div>'

    st.markdown(
        f"""
        <div style="margin-top: 1.25rem;">
            <div style="display: flex; align-items: center;">
                <h3 style="margin: 0; font-size: 1.18rem; font-weight: 600; color: {TEXT_PRIMARY};">{title}</h3>
                {badge_html}
            </div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_metric_card(
    label: str,
    value: str | int | float,
    subtext: str | None = None,
    badge: str | None = None,
    badge_variant: str = "indigo"
) -> None:
    """Renders an aesthetic, structured KPI metric card."""
    badge_html = f'<span class="cogni-badge cogni-badge-{badge_variant}" style="font-size: 0.72rem; padding: 0.15rem 0.5rem;">{badge}</span>' if badge else ""
    subtext_html = f'<div style="font-size: 0.8rem; color: {TEXT_SECONDARY}; margin-top: 0.35rem;">{subtext}</div>' if subtext else ""

    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid {BORDER_COLOR};
            border-radius: 10px;
            padding: 1.1rem 1.25rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
        ">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
                <span style="font-size: 0.82rem; font-weight: 600; color: {TEXT_SECONDARY}; text-transform: uppercase; letter-spacing: 0.04em;">{label}</span>
                {badge_html}
            </div>
            <div style="font-size: 1.75rem; font-weight: 700; color: {TEXT_PRIMARY}; line-height: 1.2;">{value}</div>
            {subtext_html}
        </div>
        """,
        unsafe_allow_html=True
    )


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

    st.markdown(
        f"""
        <div style="
            background-color: {bg_color};
            border: 1px solid {border_color}40;
            border-left: 4px solid {border_color};
            border-radius: 8px;
            padding: 0.85rem 1.15rem;
            margin-bottom: 1rem;
        ">
            <div style="font-weight: 600; font-size: 0.94rem; color: {TEXT_PRIMARY}; margin-bottom: 0.2rem;">
                {icon_str}{title}
            </div>
            <div style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.45;">
                {message}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_empty_state(title: str, description: str, icon: str = "📂") -> None:
    """Renders a friendly, clean empty state container."""
    st.markdown(
        f"""
        <div style="
            text-align: center;
            padding: 3rem 1.5rem;
            background: #FFFFFF;
            border: 1px dashed {BORDER_COLOR};
            border-radius: 12px;
            margin: 1.5rem 0;
        ">
            <div style="font-size: 2.25rem; margin-bottom: 0.75rem;">{icon}</div>
            <div style="font-size: 1.1rem; font-weight: 600; color: {TEXT_PRIMARY}; margin-bottom: 0.35rem;">{title}</div>
            <div style="font-size: 0.9rem; color: {TEXT_SECONDARY}; max-width: 480px; margin: 0 auto;">{description}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


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
    source_info = f'<span style="color: {TEXT_MUTED}; font-size: 0.78rem;">Source: {source_path}</span>' if source_path else ""

    st.markdown(
        f"""
        <div class="citation-card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.45rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-weight: 700; color: {ACCENT_INDIGO}; font-size: 0.92rem;">[{index}] Evidence <code style="color: {ACCENT_INDIGO};">{evidence_id}</code></span>
                    <span class="cogni-badge cogni-badge-neutral">{modality.upper()}</span>
                    <span class="cogni-badge cogni-badge-indigo">{locator_str}</span>
                </div>
                <span style="font-size: 0.85rem; font-weight: 500; color: {TEXT_PRIMARY};">{source_title}</span>
            </div>
            <div style="
                font-size: 0.9rem;
                color: {TEXT_PRIMARY};
                background: #FFFFFF;
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 0.65rem 0.85rem;
                font-style: italic;
                line-height: 1.45;
            ">
                "{snippet}"
            </div>
            {source_info}
        </div>
        """,
        unsafe_allow_html=True
    )
