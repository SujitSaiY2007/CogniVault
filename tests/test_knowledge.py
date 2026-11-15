from app.knowledge import find_definitions
from app.models import EvidenceUnit, Modality


def _unit(text, eid="e1"):
    return EvidenceUnit(evidence_id=eid, source_id="s", modality=Modality.text, text=text)


def test_definitions_are_found_and_pronouns_rejected():
    defs = find_definitions([_unit("Inertia is the tendency of an object to resist changes in motion.\nIt is a property of mass that matters a lot.")])
    assert [d.term for d in defs] == ["Inertia"]


def test_demo_topics_have_sensible_names_and_prerequisites(seeded):
    topics = {t.name: t for t in seeded.db.topics("public")}
    assert {"Newton's Second Law", "Linear Momentum", "Kinetic and Potential Energy", "Rules of Differentiation"} <= set(topics)
    by_id = {t.topic_id: t.name for t in topics.values()}
    assert "Newton's Second Law" in [by_id[p] for p in topics["Linear Momentum"].prerequisites]
    assert "The Derivative" in [by_id[p] for p in topics["Rules of Differentiation"].prerequisites]
    # no cross-subject noise edges
    assert not any(by_id[p].startswith("Work") for p in topics["The Derivative"].prerequisites)


def test_prerequisite_graph_is_acyclic(seeded):
    graph = {t.topic_id: t.prerequisites for t in seeded.db.topics("public")}

    def visit(n, stack):
        assert n not in stack, f"cycle through {n}"
        for p in graph.get(n, []):
            visit(p, stack | {n})

    for n in graph:
        visit(n, set())


def test_every_unit_is_tagged_to_a_topic(seeded):
    units = seeded.db.evidence_for_owner("public")
    assert units and all(u.topics for u in units)
