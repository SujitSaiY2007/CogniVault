"""
Evidence Explorer View.
Browse, search, and audit multimodal evidence units, exact source locators,
and embedded figures with verifiable provenance.
"""
from __future__ import annotations

import streamlit as st
from app.models import Modality


def render_evidence_view(services: dict):
    db = services["db"]
    st.header("🔍 Evidence Explorer & Provenance Auditor")
    st.markdown(
        """
        Inspect the atomic evidence vault. Every factual claim, tutor explanation, and assessment item
        in CogniVault is strictly traceable to these verified, addressable units.
        """
    )

    all_evidence = list(db.all_evidence())
    all_topics = [t.name for t in db.all_topics()]

    if not all_evidence:
        st.info("No evidence units indexed yet. Go to **Course Setup & Ingestion** to index materials.")
        return

    # Filter Bar
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_query = st.text_input("🔎 Search Evidence Text", placeholder="e.g., Newton's second law, derivative, chloroplast")
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

    st.markdown(f"**Showing {len(filtered)} of {len(all_evidence)} total evidence units**")

    # Display evidence cards
    for idx, ev in enumerate(filtered[:50], 1):
        source = db.get_source(ev.source_id)
        source_title = source.title if source else ev.source_id

        # Format locator
        loc = ev.location
        if "page" in loc:
            loc_badge = f"📄 Page {loc['page']}"
        elif "slide" in loc:
            loc_badge = f"📊 Slide {loc['slide']}"
        elif "timestamp" in loc:
            loc_badge = f"⏱️ Timestamp {loc['timestamp']}"
        else:
            loc_badge = "📍 Section"

        with st.container(border=True):
            header_col1, header_col2 = st.columns([3, 1])
            with header_col1:
                st.markdown(f"### `{ev.evidence_id}` — {source_title}")
            with header_col2:
                st.markdown(f"`{ev.modality.value.upper()}` | **{loc_badge}**")

            st.write(ev.text)

            # If image asset present, render the image
            if ev.asset_id:
                asset = db.get_asset(ev.asset_id)
                if asset:
                    asset_bytes = asset.get("data") if isinstance(asset, dict) else (asset[6] if len(asset) > 6 else None)
                    if asset_bytes:
                        st.image(
                            asset_bytes,
                            caption=f"Embedded Visual Figure ({ev.evidence_id}) - {loc_badge}",
                            use_container_width=False,
                            width=320
                        )

            # Metadata tags
            tag_cols = st.columns([1, 1, 2])
            with tag_cols[0]:
                if ev.topics:
                    st.caption(f"**Topics:** {', '.join(ev.topics)}")
            with tag_cols[1]:
                if ev.concepts:
                    st.caption(f"**Concepts:** {', '.join(ev.concepts)}")
            with tag_cols[2]:
                if ev.prerequisites:
                    st.caption(f"**Prerequisites:** {', '.join(ev.prerequisites)}")

    if len(filtered) > 50:
        st.info(f"Displaying first 50 results. Refine search query to inspect specific units.")
