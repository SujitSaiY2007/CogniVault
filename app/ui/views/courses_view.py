"""Human-centred course catalogue and course resource management."""
from __future__ import annotations

from pathlib import Path
import uuid

import streamlit as st


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

    st.caption("YOUR LEARNING LIBRARY")
    st.title("Courses")
    st.markdown("Keep related learning materials together. Open an original file or explore the indexed content used by the tutor.")

    top_left, top_right = st.columns([3, 1])
    with top_left:
        query = st.text_input(
            "Search courses",
            placeholder="Find a course by name…",
            label_visibility="collapsed",
            key="course_catalogue_search",
        )
    with top_right:
        st.caption(f"{len(courses)} course{'s' if len(courses) != 1 else ''} · {len(sources)} uploaded resource{'s' if len(sources) != 1 else ''}")

    with st.expander("＋ Create a course", expanded=not courses):
        with st.form("create_course_form", clear_on_submit=True):
            title = st.text_input("Course name", placeholder="e.g. Mathematics")
            description = st.text_area("Description", placeholder="What will learners study in this course?")
            submitted = st.form_submit_button("Create course", type="primary")
            if submitted:
                if not title.strip():
                    st.error("Enter a course name.")
                else:
                    try:
                        db.create_course(f"course_{uuid.uuid4().hex[:12]}", title.strip(), description.strip())
                        st.success("Course created.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not create the course: {exc}")

    visible = [
        course for course in courses
        if not query.strip()
        or query.casefold() in course["title"].casefold()
        or query.casefold() in course["description"].casefold()
    ]
    if not visible:
        if courses:
            st.info("No courses match that search.")
        else:
            with st.container(border=True):
                st.subheader("Your course library starts here")
                st.write("Create a course, then add learning materials that belong to it.")
                if st.button("Add learning materials", type="primary"):
                    st.session_state["nav_selection_override"] = "➕ Add Materials"
                    st.rerun()
        _render_resource_library(db, courses, sources)
        return

    labels = {f"{c['title']} · {c['resource_count']} materials": c["course_id"] for c in visible}
    selected_label = st.selectbox("Choose a course", list(labels), key="selected_course_label")
    selected_id = labels[selected_label]
    course = next(c for c in visible if c["course_id"] == selected_id)
    resources = db.get_course_resources(selected_id)

    with st.container(border=True):
        title_col, count_col = st.columns([4, 1])
        with title_col:
            st.caption("SELECTED COURSE")
            st.subheader(course["title"])
            st.write(course["description"] or "Add a description to help learners understand what this course covers.")
        with count_col:
            st.metric("Materials", len(resources))

        st.divider()
        st.subheader("Learning materials")
        if resources:
            for source in resources:
                with st.container(border=True):
                    info_col, actions_col = st.columns([2.5, 1])
                    with info_col:
                        st.markdown(f"**{source.title}**")
                        excerpt_count = len(db.get_evidence_for_source(source.source_id))
                        st.caption(
                            f"{source.modality.value.upper()} · "
                            f"{excerpt_count} searchable excerpts"
                        )
                    with actions_col:
                        path = _resolve_source_path(source.path)
                        if path:
                            try:
                                st.download_button(
                                    "Open original",
                                    data=path.read_bytes(),
                                    file_name=path.name,
                                    mime=_mime_for(path),
                                    key=f"course_download_{selected_id}_{source.source_id}",
                                    use_container_width=True,
                                )
                            except OSError:
                                st.caption("Original file could not be read.")
                        else:
                            st.caption("Original file is not available at its saved path.")
                        if st.button(
                            "Explore content",
                            key=f"course_evidence_{selected_id}_{source.source_id}",
                            use_container_width=True,
                        ):
                            st.session_state["library_source_filter"] = source.source_id
                            st.session_state["nav_selection_override"] = "🔎 Evidence Explorer"
                            st.rerun()
                        if st.button(
                            "Remove from course",
                            key=f"course_unlink_{selected_id}_{source.source_id}",
                            use_container_width=True,
                        ):
                            db.remove_source_from_course(selected_id, source.source_id)
                            st.rerun()
        else:
            st.info("This course has no materials yet. Add an uploaded file below.")

        available = [
            source for source in sources
            if source.source_id not in {item.source_id for item in resources}
        ]
        with st.expander("＋ Add uploaded materials", expanded=not resources and bool(available)):
            if not available:
                st.write("No unassigned uploaded materials are available yet.")
                if st.button("Upload learning materials", type="primary", key="empty_course_upload"):
                    st.session_state["nav_selection_override"] = "➕ Add Materials"
                    st.rerun()
            else:
                source_labels = {
                    f"{source.title} · {source.modality.value.upper()}": source.source_id
                    for source in available
                }
                chosen = st.multiselect(
                    "Select one or more materials",
                    options=list(source_labels),
                    key=f"assign_materials_{selected_id}",
                )
                if st.button(
                    "Add to course",
                    type="primary",
                    disabled=not chosen,
                    key=f"assign_submit_{selected_id}",
                ):
                    for label in chosen:
                        db.assign_source_to_course(selected_id, source_labels[label])
                    st.rerun()

    _render_resource_library(db, courses, sources)


def _render_resource_library(db, courses: list, sources: list) -> None:
    assigned_ids = {
        resource.source_id
        for course in courses
        for resource in db.get_course_resources(course["course_id"])
    }
    unassigned = [source for source in sources if source.source_id not in assigned_ids]
    with st.expander(f"Resource library · {len(unassigned)} unassigned"):
        st.write("Uploaded files that have not yet been added to a course.")
        if not unassigned:
            st.caption("All uploaded resources are assigned to a course, or no resources have been uploaded.")
        else:
            for source in unassigned:
                col_info, col_action = st.columns([3, 1])
                with col_info:
                    st.markdown(f"**{source.title}**")
                    st.caption(f"{source.modality.value.upper()} · {len(db.get_evidence_for_source(source.source_id))} searchable excerpts")
                with col_action:
                    if st.button("Add to a course", key=f"unassigned_add_{source.source_id}", use_container_width=True):
                        st.info("Choose a course above, then use “Add uploaded materials”.")
        if st.button("Upload learning materials", type="primary", key="course_library_upload"):
            st.session_state["nav_selection_override"] = "➕ Add Materials"
            st.rerun()
