"""
Evidence Explorer View.
Browse, search, and audit multimodal evidence units, exact source locators,
and embedded figures with verifiable provenance.
"""
from __future__ import annotations

import streamlit as st
from app.models import Modality
from app.ui.components import (
    _render_html_fragment,
    render_page_header,
    render_section_header,
    render_metric_card,
    render_empty_state,
)


def render_evidence_view(services: dict):
    db = services["db"]

    render_page_header(
        title="Evidence Explorer & Provenance Auditor",
        description="Inspect atomic curriculum evidence units, exact physical source locators, embedded figures, and taxonomy relationships.",
        badge_text="Module 2",
        badge_variant="teal"
    )

    all_evidence = list(db.all_evidence())
    all_topics = [t.name for t in db.all_topics()]
    sources = list(db.all_sources())

    if not all_evidence:
        render_empty_state(
            title="Evidence Vault is Empty",
            description="No evidence units indexed yet. Navigate to 'Course Setup & Ingestion' to upload documents or seed the default corpus.",
            icon="📂"
        )
        return

    # Modality and Asset counts
    modalities_present = set(e.modality.value.upper() for e in all_evidence)
    asset_units = sum(1 for e in all_evidence if e.asset_id)

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        render_metric_card("Total Evidence Units", len(all_evidence), subtext="Indexed atomic chunks", badge="Verified", badge_variant="teal")
    with col_m2:
        render_metric_card("Modality Types", len(modalities_present), subtext="/".join(sorted(modalities_present)), badge="Multi-Modal", badge_variant="indigo")
    with col_m3:
        render_metric_card("Visual Figures", asset_units, subtext="Embedded image assets", badge="Figures", badge_variant="neutral")
    with col_m4:
        render_metric_card("Associated Topics", len(all_topics), subtext="Curriculum breadth", badge="Taxonomy", badge_variant="success")

    _render_html_fragment("<div style='margin-bottom: 1.25rem;'></div>")

    # Search and Filter Workspace Card
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_query = st.text_input("🔎 Search Evidence Text & Concepts", placeholder="e.g., Newton's second law, derivative, chloroplast")
        with col2:
            selected_topic = st.selectbox("Topic Filter", ["All Topics"] + all_topics)
        with col3:
            selected_modality = st.selectbox("Modality Filter", ["All Modalities", "PDF", "PPTX", "TRANSCRIPT", "IMAGE"])

    # Filtering logic
    filtered = all_evidence

    if selected_topic != "All Topics":
        filtered = [e for e in filtered if selected_topic in e.topics or any(selected_topic.lower() in c.lower() for c in e.concepts)]

    if selected_modality != "All Modalities":
        mod_map = {
            "PDF": Modality.pdf,
            "PPTX": Modality.pptx,
            "TRANSCRIPT": Modality.video,
            "IMAGE": Modality.image,
        }
        target_mod = mod_map.get(selected_modality)
        if target_mod:
            filtered = [e for e in filtered if e.modality == target_mod]

    if search_query.strip():
        q_lower = search_query.strip().lower()
        filtered = [e for e in filtered if q_lower in e.text.lower() or any(q_lower in c.lower() for c in e.concepts)]

    # Result Header / Counter
    render_section_header(
        title="Evidence Units",
        subtitle=f"Displaying {min(len(filtered), 50)} of {len(filtered)} matching units (total indexed: {len(all_evidence)})",
        badge_text=f"{len(filtered)} matches" if filtered else None
    )

    if not filtered:
        render_empty_state(
            title="No Matching Evidence Units Found",
            description="Try modifying your search keywords, selecting a different topic, or clearing the modality filter.",
            icon="🔍"
        )
        return

    # Display evidence cards
    for idx, ev in enumerate(filtered[:50], 1):
        source = db.get_source(ev.source_id)
        source_title = source.title if source else ev.source_id
        source_path = source.path if source else ""

        # Format locator
        loc = ev.location
        if "page" in loc:
            loc_badge = f"📄 Page {loc['page']}"
            loc_variant = "indigo"
        elif "slide" in loc:
            loc_badge = f"📊 Slide {loc['slide']}"
            loc_variant = "teal"
        elif "timestamp" in loc:
            loc_badge = f"⏱️ Timestamp {loc['timestamp']}"
            loc_variant = "warning"
        else:
            loc_badge = "📍 Section"
            loc_variant = "neutral"

        with st.container(border=True):
            header_col1, header_col2 = st.columns([2.5, 1.2])
            with header_col1:
                _render_html_fragment(f"""
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem;">
                        <span class="cogni-badge cogni-badge-neutral" style="font-family: monospace;">{ev.evidence_id}</span>
                        <strong style="color: #18233B; font-size: 1.05rem;">{source_title}</strong>
                    </div>
                    """)
                if source_path:
                    st.caption(f"Source file: `{source_path}`")
            with header_col2:
                _render_html_fragment(f"""
                    <div style="display: flex; justify-content: flex-end; gap: 0.4rem; align-items: center;">
                        <span class="cogni-badge cogni-badge-neutral">{ev.modality.value.upper()}</span>
                        <span class="cogni-badge cogni-badge-{loc_variant}">{loc_badge}</span>
                    </div>
                    """)

            # Excerpt Box
            _render_html_fragment(f"""
                <div style="
                    background-color: #F8FAFC;
                    border-left: 3px solid #CBD5E1;
                    padding: 0.75rem 1rem;
                    border-radius: 4px;
                    margin: 0.6rem 0;
                    color: #18233B;
                    font-size: 0.94rem;
                    line-height: 1.5;
                ">
                    {ev.text}
                </div>
                """)

            # If image asset present, safely render image
            if ev.asset_id:
                asset = db.get_asset(ev.asset_id)
                if asset:
                    asset_bytes = asset.get("data") if isinstance(asset, dict) else (asset[6] if len(asset) > 6 else None)
                    if asset_bytes:
                        st.image(
                            asset_bytes,
                            caption=f"Embedded Visual Figure ({ev.evidence_id}) - {loc_badge}",
                            use_container_width=False,
                            width=340
                        )

            # Metadata tags
            tag_parts = []
            if ev.topics:
                tag_parts.append(f"**Topics:** {', '.join(ev.topics)}")
            if ev.concepts:
                tag_parts.append(f"**Concepts:** {', '.join(ev.concepts)}")
            if ev.prerequisites:
                tag_parts.append(f"**Prerequisites:** {', '.join(ev.prerequisites)}")

            if tag_parts:
                _render_html_fragment(f"<div style='font-size: 0.82rem; color: #64748B; margin-top: 0.35rem;'>"
                    + " &nbsp;|&nbsp; ".join(tag_parts)
                    + "</div>")

    if len(filtered) > 50:
        st.info("Displaying first 50 results. Refine search query to inspect specific units.")
