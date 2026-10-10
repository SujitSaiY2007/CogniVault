"""
Course Setup & Document Ingestion View.
Allows uploading and indexing PDFs, PPTX slide decks, and video/audio transcripts,
or 1-click deterministic seeding of the reproducible School Mathematics & Science corpus.
"""
from __future__ import annotations

import os
from pathlib import Path
import streamlit as st
import pandas as pd

from app.ingest import ingest_file
from app.corpus import seed_database_from_corpus, get_corpus_manifest
from app.ui.components import (
    _render_html_fragment,
    render_page_header,
    render_section_header,
    render_metric_card,
    render_callout,
    render_empty_state,
)


def render_ingestion_view(services: dict):
    db = services["db"]

    render_page_header(
        title="Course Setup & Ingestion",
        description="Ingest multi-modal course materials into CogniVault's verifiable evidence vault with deterministic provenance, exact locators, and SHA-256 checksums.",
        badge_text="Module 1",
        badge_variant="indigo"
    )

    sources = list(db.all_sources())
    all_evidence = list(db.all_evidence())
    all_topics = db.all_topics()
    all_concepts = db.all_concepts()
    verified_questions = db.all_questions(verified_only=True)

    # Top-level KPI overview cards
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        render_metric_card("Indexed Sources", len(sources), subtext="Multi-modal documents", badge="Raw Sources", badge_variant="indigo")
    with col_m2:
        render_metric_card("Evidence Units", len(all_evidence), subtext="Addressable chunks", badge="Atomic Chunks", badge_variant="teal")
    with col_m3:
        render_metric_card("Topics & Concepts", f"{len(all_topics)} / {len(all_concepts)}", subtext="Knowledge taxonomy", badge="Curriculum", badge_variant="neutral")
    with col_m4:
        render_metric_card("Verified Questions", len(verified_questions), subtext="100% Structural integrity", badge="Practice Items", badge_variant="success")

    _render_html_fragment("<div style='margin-bottom: 1.5rem;'></div>")

    # Ingestion Actions: Upload and Seed Corpus
    col1, col2 = st.columns([1.2, 1])

    with col1:
        with st.container(border=True):
            render_section_header("Upload Course Material", subtitle="Extract text, slide structures, timestamps, and embedded diagrams.")
            st.markdown(
                """
                <div style="display: flex; gap: 0.5rem; margin-bottom: 0.75rem;">
                    <span class="cogni-badge cogni-badge-neutral">📄 PDF (Text & Figures)</span>
                    <span class="cogni-badge cogni-badge-neutral">📊 PPTX (Slides & Notes)</span>
                    <span class="cogni-badge cogni-badge-neutral">⏱️ Transcripts ([hh:mm:ss])</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            uploaded_files = st.file_uploader(
                "Select educational documents to index",
                type=["pdf", "pptx", "txt"],
                accept_multiple_files=True,
                help="Extracts text, slide structures, timestamps, and embedded diagrams with exact source locators.",
                label_visibility="collapsed"
            )

            if uploaded_files:
                if st.button("🚀 Process & Ingest Files", type="primary", use_container_width=True):
                    os.makedirs("data/uploads", exist_ok=True)
                    for uf in uploaded_files:
                        save_path = Path("data/uploads") / uf.name
                        with open(save_path, "wb") as f:
                            f.write(uf.getvalue())

                        try:
                            with st.spinner(f"Indexing {uf.name}..."):
                                sid = ingest_file(save_path, db)
                                st.success(f" Successfully indexed **{uf.name}** (Source ID: `{sid}`)")
                        except Exception as e:
                            st.error(f"❌ Failed to ingest {uf.name}: {str(e)}")

    with col2:
        with st.container(border=True):
            render_section_header("Reproducible Baseline Corpus", subtitle="Deterministic Mathematics & Science benchmark materials.")
            render_callout(
                title="Curriculum Alignment",
                message="Includes Newtonian Mechanics (PDF), Optics (PPTX), Differential Calculus (PDF), and Cellular Biology (Transcript).",
                variant="indigo",
                icon="💡"
            )
            if st.button("🔄 Reset & Re-Seed Default Corpus", use_container_width=True):
                with st.spinner("Seeding Math/Science corpus & verified question bank..."):
                    counts = seed_database_from_corpus(db)
                    ev_count = counts.get("evidence_units", counts.get("evidence", 0))
                    st.success(
                        f" Seeded {counts.get('sources', 0)} sources, {ev_count} evidence units, "
                        f"{counts.get('topics', 0)} topics, {counts.get('concepts', 0)} concepts, and {counts.get('questions', 0)} verified questions!"
                    )
                    st.rerun()

    _render_html_fragment("<div style='margin-bottom: 1rem;'></div>")

    # Display Current Ingested Sources & Manifest Summary
    render_section_header("📚 Currently Indexed Course Sources", subtitle="Every factual unit in CogniVault links directly to these indexed files.")

    if not sources:
        render_empty_state(
            title="No Course Sources Indexed",
            description="Upload educational course materials above or click 'Reset & Re-Seed Default Corpus' to load the reproducible baseline.",
            icon="📂"
        )
        return

    source_data = []
    for s in sources:
        ev_count = len(db.get_evidence_for_source(s.source_id))
        source_data.append({
            "Source ID": s.source_id,
            "Title": s.title,
            "Modality": s.modality.value.upper(),
            "File Path": s.path,
            "SHA-256 Checksum": s.sha256[:16] + "...",
            "Evidence Units": ev_count,
        })

    df = pd.DataFrame(source_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Manifest metadata view
    with st.expander("📋 View Corpus Manifest & Provenance Details", expanded=False):
        manifest = get_corpus_manifest()
        st.json(manifest)
