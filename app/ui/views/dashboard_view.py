"""Learner-first home page: orient, resume, and take one useful next step."""
from __future__ import annotations

import streamlit as st

from app.corpus import seed_database_from_corpus


def _navigate(label: str) -> None:
    st.session_state["nav_selection_override"] = label
    st.rerun()


def render_dashboard_view(services: dict) -> None:
    db = services["db"]
    recommendation_engine = services["recommendations"]
    learner_id = st.session_state.get("active_learner_id", "learner_demo")
    sources = list(db.all_sources())

    st.caption("YOUR LEARNING WORKSPACE")
    st.title("Learn with confidence.")
    st.markdown(
        "Explore your course materials, ask questions grounded in those sources, "
        "and practise the topics you want to strengthen."
    )

    # The first-run experience offers real actions, not empty dashboard metrics.
    if not sources:
        with st.container(border=True):
            st.subheader("Start with your learning materials")
            st.write(
                "Add your own PDFs, slides, or transcripts, or load the project's "
                "benchmark corpus to explore the full learning workflow."
            )
            add_col, demo_col = st.columns(2)
            with add_col:
                if st.button("＋ Add learning materials", type="primary", use_container_width=True):
                    _navigate("➕ Add Materials")
            with demo_col:
                if st.button("Load benchmark learning materials", use_container_width=True):
                    with st.spinner("Preparing the benchmark corpus…"):
                        seed_database_from_corpus(db)
                    st.rerun()
        _render_quick_actions()
        return

    interactions = db.get_interactions(learner_id)
    masteries = db.get_all_learner_masteries(learner_id)
    questions = db.all_questions(verified_only=True)
    topics = db.all_topics()

    resume_topic = None
    if interactions:
        resume_topic = interactions[-1].get("topic_id")
    elif masteries:
        resume_topic = masteries[0].topic_id
    elif topics:
        resume_topic = topics[0].name

    hero_col, resume_col = st.columns([1.25, 1], gap="large")
    with hero_col:
        with st.container(border=True):
            st.markdown("### Your materials. Your pace.")
            st.write(
                "Get answers tied to your indexed course sources, practise with verified "
                "questions, and use evidence-based guidance to choose what to study next."
            )
            st.markdown("**Built around three steps**")
            st.markdown("- Explore a course and open its learning materials")
            st.markdown("- Ask the tutor and inspect its source citations")
            st.markdown("- Practise, review feedback, and revisit topics")
            if st.button("Explore courses", type="primary", use_container_width=True):
                _navigate("📚 Courses")

    with resume_col:
        with st.container(border=True):
            st.caption("PICK UP WHERE YOU LEFT OFF")
            if resume_topic:
                st.subheader(str(resume_topic))
                mastery = db.get_learner_mastery(learner_id, resume_topic)
                if mastery:
                    st.metric("Current mastery estimate", f"{mastery.p_mastery:.0%}")
                    st.caption("A learner-model estimate, not course completion.")
                topic_questions = db.get_questions_for_topic(resume_topic, verified_only=True)
                st.caption(f"{len(topic_questions)} verified practice items available for this topic.")
                if st.button("Continue with practice", type="primary", use_container_width=True):
                    st.session_state["active_topic_id"] = resume_topic
                    _navigate("📝 Practice")
            else:
                st.subheader("Ready when you are")
                st.write("Start with a course or ask a question about your materials.")
                if st.button("Open AI Tutor", type="primary", use_container_width=True):
                    _navigate("💬 AI Tutor")
            st.divider()
            st.caption(
                f"{len(sources)} learning source{'s' if len(sources) != 1 else ''} · "
                f"{len(topics)} topics · {len(questions)} verified practice items"
            )

    st.subheader("Recommended next step")
    try:
        recommendation = recommendation_engine.recommend(learner_id)
        with st.container(border=True):
            rec_col, action_col = st.columns([3, 1])
            with rec_col:
                st.markdown(f"**{recommendation.recommended_action.replace('_', ' ').title()}**")
                st.write(recommendation.rationale)
                st.caption(
                    f"Topic: {recommendation.topic_id} · Suggested difficulty: "
                    f"{recommendation.difficulty.value}"
                )
            with action_col:
                if st.button("Take next step", type="primary", use_container_width=True):
                    destination = (
                        "💬 AI Tutor"
                        if "tutor" in recommendation.recommended_action.casefold()
                        else "📝 Practice"
                    )
                    st.session_state["active_topic_id"] = recommendation.topic_id
                    _navigate(destination)
    except Exception:
        with st.container(border=True):
            st.write("Your next study recommendation will appear when enough learner-state information is available.")
            if st.button("Start a practice session", type="primary"):
                _navigate("📝 Practice")

    _render_quick_actions()


def _render_quick_actions() -> None:
    st.subheader("Quick actions")
    actions = [
        ("💬", "Ask the tutor", "💬 AI Tutor"),
        ("📝", "Practise a topic", "📝 Practice"),
        ("📚", "Browse courses", "📚 Courses"),
        ("＋", "Add materials", "➕ Add Materials"),
    ]
    cols = st.columns(len(actions))
    for col, (icon, title, target) in zip(cols, actions):
        with col:
            with st.container(border=True):
                st.markdown(f"### {icon}")
                st.markdown(f"**{title}**")
                if st.button("Open", key=f"home_action_{target}", use_container_width=True):
                    _navigate(target)
