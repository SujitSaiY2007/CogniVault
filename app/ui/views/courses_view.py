"""Human-friendly course library for indexed learning resources."""
from __future__ import annotations

from pathlib import Path
import streamlit as st

from app.ui.components import render_page_header, render_empty_state, render_section_header


def _resolve_source_path(raw_path: str) -> Path | None:
    candidate = Path(raw_path).expanduser()
    candidates = [candidate]
    if not candidate.is_absolute():
        candidates.append(Path.cwd() / candidate)
        candidates.append(Path(__file__).resolve().parents[3] / candidate)
    for path in candidates:
        try:
            if path.is_file():
                return path.resolve()
        except OSError:
            continue
    return None


def render_courses_view(services: dict) -> None:
    db = services["db"]
    sources = list(db.all_sources())

    render_page_header(
        title="Your Course Library",
        description="Open the original learning materials used by CogniVault, see what has been indexed, or add and manage resources.",
        badge_text="Learning Library",
        badge_variant="teal",
    )

    add_col, count_col = st.columns([1, 2])
    with add_col:
        if st.button("＋ Add course material", type="primary", use_container_width=True):
            st.session_state["nav_selection_override"] = "➕ New Course"
            st.rerun()
    with count_col:
        st.caption(f"{len(sources)} resource{'s' if len(sources) != 1 else ''} available in this local library")

    st.info(
        "A resource is a PDF, slide deck, transcript, or other supported file. "
        "CogniVault indexes its content for grounded answers; this page helps you find the original file."
    )

    if not sources:
        render_empty_state(
            title="Your library is empty",
            description="Add a PDF, PowerPoint, or text transcript to start building your course library.",
            icon="📚",
        )
        return

    query = st.text_input("Search your library", placeholder="Search by course or file name…", key="course_library_search")
    filtered = [
        source for source in sources
        if not query.strip() or query.strip().lower() in source.title.lower()
        or query.strip().lower() in Path(source.path).name.lower()
    ]
    render_section_header("Learning resources", subtitle="Choose a resource to open its original file or inspect its indexed content.", badge_text=f"{len(filtered)} found")

    if not filtered:
        st.warning("No resources match that search. Try another title or clear the search.")
        return

    for source in filtered:
        evidence_count = len(db.get_evidence_for_source(source.source_id))
        path = _resolve_source_path(source.path)
        with st.container(border=True):
            title_col, meta_col = st.columns([3, 1])
            with title_col:
                st.markdown(f"### {source.title}")
                st.caption(f"{source.modality.value.upper()} · {evidence_count} searchable learning excerpts")
                st.caption(f"File: {Path(source.path).name}")
            with meta_col:
                st.metric("Learning excerpts", evidence_count)

            action_cols = st.columns([1.15, 1.15, 1.1, 2])
            with action_cols[0]:
                if path:
                    try:
                        st.download_button(
                            "⬇ Download original",
                            data=path.read_bytes(),
                            file_name=path.name,
                            mime="application/pdf" if path.suffix.lower() == ".pdf" else (
                                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                                if path.suffix.lower() == ".pptx" else "text/plain"
                            ),
                            key=f"download_{source.source_id}",
                            use_container_width=True,
                        )
                    except OSError:
                        st.warning("Original file cannot be read from disk.")
                else:
                    st.button("Original unavailable", disabled=True, key=f"missing_{source.source_id}", use_container_width=True)
            with action_cols[1]:
                if st.button("View excerpts", key=f"view_{source.source_id}", use_container_width=True):
                    st.session_state["library_source_filter"] = source.source_id
                    st.session_state["nav_selection_override"] = "🔎 Evidence Explorer"
                    st.rerun()
            with action_cols[2]:
                with st.popover("Manage", use_container_width=True):
                    st.caption("Removing a resource also removes its indexed excerpts and questions that cite those excerpts. The original file on disk is not deleted.")
                    confirmed = st.checkbox("I understand; remove this resource from CogniVault", key=f"confirm_delete_{source.source_id}")
                    if st.button("Remove from library", key=f"delete_{source.source_id}", type="secondary", disabled=not confirmed, use_container_width=True):
                        try:
                            if db.delete_source(source.source_id):
                                st.session_state.pop(f"confirm_delete_{source.source_id}", None)
                                st.success(f"Removed {source.title} from the indexed library.")
                                st.rerun()
                            else:
                                st.error("This resource was already removed.")
                        except Exception as exc:
                            st.error(f"Could not remove this resource: {exc}")

            with st.expander("Resource details"):
                st.write("**Where it is stored**")
                st.code(str(path) if path else source.path, language=None)
                st.write("**Integrity checksum (SHA-256)**")
                st.code(source.sha256, language=None)
                st.write("**Resource ID**")
                st.code(source.source_id, language=None)
