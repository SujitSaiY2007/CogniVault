"""
Course Setup & Document Ingestion View.
Allows uploading and indexing PDFs, PPTX slide decks, and video/audio transcripts,
or 1-click seeding of the reproducible school Mathematics & Science corpus.
"""
from __future__ import annotations

import os
from pathlib import Path
import streamlit as st
import pandas as pd

from app.ingest import ingest_file
from app.corpus import seed_database_from_corpus, get_corpus_manifest


def render_ingestion_view(services: dict):
    db = services["db"]
    st.header("📥 Course Setup & Ingestion")
    st.markdown(
        """
        Ingest multi-modal course materials into CogniVault's verifiable evidence vault.
        Supported formats: **PDF Documents** (text & embedded figures), **PPTX Slide Decks** (shapes & slide notes), and **Transcripts** (`[hh:mm:ss]` timestamps).
        """
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Upload Course Material")
        uploaded_files = st.file_uploader(
            "Select educational files to ingest",
            type=["pdf", "pptx", "txt"],
            accept_multiple_files=True,
            help="Extracts text, slide structures, timestamps, and embedded diagrams with exact source locators."
        )

        if uploaded_files:
            if st.button("🚀 Process & Ingest Files", type="primary"):
                os.makedirs("data/uploads", exist_ok=True)
                for uf in uploaded_files:
                    save_path = Path("data/uploads") / uf.name
                    with open(save_path, "wb") as f:
                        f.write(uf.getvalue())

                    try:
                        with st.spinner(f"Ingesting {uf.name}..."):
                            sid = ingest_file(save_path, db)
                            st.success(f" Successfully indexed **{uf.name}** (Source ID: `{sid}`)")
                    except Exception as e:
                        st.error(f"❌ Failed to ingest {uf.name}: {str(e)}")

    with col2:
        st.subheader("Reproducible Corpus")
        st.info("Load the official, reproducible School Mathematics & Science baseline corpus.")
        if st.button("🔄 Reset & Re-Seed Default Corpus", use_container_width=True):
            with st.spinner("Seeding Math/Science corpus & verified question bank..."):
                counts = seed_database_from_corpus(db)
                st.success(
                    f" Seeded {counts['sources']} sources, {counts['evidence']} evidence units, "
                    f"{counts['topics']} topics, {counts['concepts']} concepts, and {counts['questions']} verified questions!"
                )
                st.rerun()

    st.divider()

    # Display Current Ingested Sources & Manifest Summary
    st.subheader("📚 Currently Indexed Course Sources")
    sources = list(db.all_sources())

    if not sources:
        st.warning("No course sources indexed yet. Upload a document or click 'Re-Seed Default Corpus' above.")
        return

    source_data = []
    for s in sources:
        # Count evidence units
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
    with st.expander("📋 View Corpus Manifest & Provenance Details"):
        manifest = get_corpus_manifest()
        st.json(manifest)
