"""Student-facing course catalogue with resources organized inside each course."""
from __future__ import annotations

from pathlib import Path
import uuid
import streamlit as st

from app.ui.components import render_page_header, render_empty_state, render_section_header


def _resolve_source_path(raw_path: str) -> Path | None:
    candidate = Path(raw_path).expanduser()
    candidates = [candidate]
    if not candidate.is_absolute():
        candidates.extend([Path.cwd() / candidate, Path(__file__).resolve().parents[3] / candidate])
    for path in candidates:
        try:
            if path.is_file():
                return path.resolve()
        except OSError:
            continue
    return None


def _mime_for(path: Path) -> str:
    return {
        ".pdf": "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".txt": "text/plain",
    }.get(path.suffix.lower(), "application/octet-stream")


def render_courses_view(services: dict) -> None:
    db = services["db"]
    courses = db.all_courses()
    sources = list(db.all_sources())

    render_page_header(
        title="Available Courses",
        description="Choose a course to explore its learning materials. Each course groups related resources, topics, and practice.",
        badge_text="Course catalogue",
        badge_variant="teal",
    )

    with st.expander("＋ Create a course", expanded=not courses):
        with st.form("create_course_form", clear_on_submit=True):
            title = st.text_input("Course name", placeholder="e.g., Mathematics")
            description = st.text_area("What will learners study?", placeholder="A short course description")
            submitted = st.form_submit_button("Create course", type="primary")
            if submitted:
                if not title.strip():
                    st.error("Enter a course name.")
                else:
                    try:
                        db.create_course(f"course_{uuid.uuid4().hex[:12]}", title, description)
                        st.success(f"Created course: {title.strip()}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not create this course: {exc}")

    if not courses:
        render_empty_state(
            title="No courses yet",
            description="Create your first course, then add PDFs, slide decks, or transcripts as learning materials.",
            icon="🎓",
        )
        if st.button("Add learning materials", type="primary"):
            st.session_state["nav_selection_override"] = "➕ New Course"
            st.rerun()
        return

    query = st.text_input("Find a course", placeholder="Search course names or descriptions…", key="available_course_search")
    visible = [c for c in courses if not query.strip() or query.casefold() in c["title"].casefold() or query.casefold() in c["description"].casefold()]
    st.caption(f"{len(visible)} course{'s' if len(visible) != 1 else ''} · {sum(c['resource_count'] for c in courses)} course-resource links")

    if not visible:
        st.info("No courses match that search.")
        return

    for course in visible:
        with st.container(border=True):
            title_col, count_col = st.columns([4, 1])
            with title_col:
                st.subheader(f"🎓 {course['title']}")
                st.write(course["description"] or "Learning materials and practice for this course.")
            with count_col:
                st.metric("Materials", course["resource_count"])

            resources = db.get_course_resources(course["course_id"])
            if resources:
                st.markdown("**Course materials**")
                for source in resources:
                    resource_col, action_col = st.columns([4, 1])
                    with resource_col:
                        st.write(f"📄 {source.title}")
                        st.caption(f"{source.modality.value.upper()} · {len(db.get_evidence_for_source(source.source_id))} searchable excerpts")
                    with action_col:
                        path = _resolve_source_path(source.path)
                        if path:
                            try:
                                st.download_button(
                                    "Open / Download",
                                    data=path.read_bytes(),
                                    file_name=path.name,
                                    mime=_mime_for(path),
                                    key=f"course_download_{course['course_id']}_{source.source_id}",
                                    use_container_width=True,
                                )
                            except OSError:
                                st.caption("File unavailable")
                        else:
                            st.caption("Original file unavailable")
                        if st.button("View content", key=f"course_evidence_{course['course_id']}_{source.source_id}", use_container_width=True):
                            st.session_state["library_source_filter"] = source.source_id
                            st.session_state["nav_selection_override"] = "🔎 Evidence Explorer"
                            st.rerun()
                        if st.button("Remove from course", key=f"course_unlink_{course['course_id']}_{source.source_id}", use_container_width=True):
                            db.remove_source_from_course(course["course_id"], source.source_id)
                            st.rerun()
            else:
                st.info("No materials have been added to this course yet.")

            available = [s for s in sources if s.source_id not in {r.source_id for r in resources}]
            with st.expander("＋ Add existing material to this course"):
                if not available:
                    st.caption("No unassigned resources are available. Upload materials using New Course in the sidebar, then return here.")
                else:
                    labels = {f"{s.title} · {s.modality.value.upper()}": s.source_id for s in available}
                    selected = st.multiselect(
                        "Choose uploaded materials",
                        options=list(labels),
                        key=f"assign_materials_{course['course_id']}",
                    )
                    if st.button("Add selected materials", key=f"assign_submit_{course['course_id']}", type="primary", disabled=not selected):
                        for label in selected:
                            db.assign_source_to_course(course["course_id"], labels[label])
                        st.rerun()

    st.divider()
    with st.expander("Resource library (advanced)"):
        st.caption("Uploaded files not yet organized into a course are listed here. Add them to a course above.")
        assigned_ids = {r.source_id for c in courses for r in db.get_course_resources(c["course_id"])}
        unassigned = [s for s in sources if s.source_id not in assigned_ids]
        if not unassigned:
            st.success("Every uploaded resource is assigned to at least one course.")
        else:
            for source in unassigned:
                st.write(f"📄 **{source.title}** — {source.modality.value.upper()}")
                st.caption(source.path)
        if st.button("Upload learning materials", type="primary", key="course_library_upload"):
            st.session_state["nav_selection_override"] = "➕ New Course"
            st.rerun()
