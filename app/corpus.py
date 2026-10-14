from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
import pymupdf
from pptx import Presentation
from pptx.util import Inches, Pt

from .db import EvidenceDB
from .ingest import ingest_pdf, ingest_pptx, ingest_transcript
from .models import (
    Difficulty,
    QuestionOption,
    QuestionType,
)
from .assessment import AssessmentEngine

import io
from PIL import Image, ImageDraw

def get_diagram_png_bytes() -> bytes:
    img = Image.new("RGB", (200, 200), color=(240, 245, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 180, 180], outline=(40, 80, 180), width=3)
    draw.line([100, 30, 100, 170], fill=(220, 50, 50), width=2)
    draw.line([30, 100, 170, 100], fill=(50, 180, 50), width=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def create_physics_pdf(file_path: Path) -> str:
    doc = pymupdf.open()

    # Page 1: Newton's Laws
    p1 = doc.new_page()
    p1.insert_text(
        (50, 60),
        "CogniVault School Science: Classical Mechanics & Dynamics\n\n"
        "1. Newton's First Law of Motion (Law of Inertia):\n"
        "An object remains at rest or in uniform motion in a straight line unless acted upon by an external net force.\n\n"
        "2. Newton's Second Law of Motion:\n"
        "The acceleration of an object is directly proportional to the net force acting upon it and inversely proportional to its mass: F = m * a.\n"
        "Where F is force in Newtons (N), m is mass in kilograms (kg), and a is acceleration in m/s^2.\n\n"
        "3. Newton's Third Law of Motion:\n"
        "For every action, there is an equal and opposite reaction (F_AB = -F_BA).\n"
    )

    # Page 2: Momentum and Work-Energy with Diagram
    p2 = doc.new_page()
    p2.insert_text(
        (50, 60),
        "4. Linear Momentum:\n"
        "Linear momentum p is the product of mass and velocity: p = m * v.\n"
        "In an isolated system, total momentum is conserved during all collisions.\n\n"
        "5. Mechanical Work & Kinetic Energy:\n"
        "Work done by a constant force is the product of force and displacement in the direction of force: W = F * d.\n"
        "Kinetic Energy of a body of mass m moving with speed v is given by E_k = 0.5 * m * v^2.\n"
        "Figure 1.1: Free-body force vector diagram showing balanced normal and gravitational forces."
    )
    p2.insert_image(pymupdf.Rect(50, 260, 250, 460), stream=get_diagram_png_bytes())

    doc.save(file_path)
    doc.close()

    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()

def create_optics_pptx(file_path: Path) -> str:
    prs = Presentation()

    # Slide 1: Wave Fundamentals
    slide1 = prs.slides.add_slide(prs.slide_layouts[1])
    slide1.shapes.title.text = "Wave Properties & The Wave Equation"
    slide1.shapes.placeholders[1].text = (
        "Wave speed equation relates propagation speed (v), frequency (f), and wavelength (lambda):\n"
        "v = f * lambda\n\n"
        "Frequency is measured in Hertz (Hz), wavelength in meters (m), and wave speed in m/s.\n"
        "Wave frequency remains constant when passing from one medium to another."
    )

    # Slide 2: Geometric Optics & Refraction
    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Laws of Reflection & Snell's Law of Refraction"
    slide2.shapes.placeholders[1].text = (
        "Law of Reflection: The angle of incidence equals the angle of reflection (theta_i = theta_r).\n\n"
        "Snell's Law of Refraction: Describes bending of light at the boundary between two media:\n"
        "n1 * sin(theta1) = n2 * sin(theta2)\n\n"
        "Where n1 and n2 are the refractive indices of medium 1 and medium 2 respectively."
    )

    prs.save(file_path)
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()

def create_math_pdf(file_path: Path) -> str:
    doc = pymupdf.open()

    # Page 1: Algebra & Quadratic Formula
    p1 = doc.new_page()
    p1.insert_text(
        (50, 60),
        "CogniVault School Mathematics: Algebra to Introductory Calculus\n\n"
        "1. Quadratic Equations & Quadratic Formula:\n"
        "A standard quadratic equation has the form ax^2 + bx + c = 0, where a != 0.\n"
        "The roots of the quadratic equation are given by the Quadratic Formula:\n"
        "x = (-b +- sqrt(b^2 - 4ac)) / (2a).\n"
        "The discriminant D = b^2 - 4ac determines the nature of roots:\n"
        "- D > 0: two distinct real roots\n"
        "- D = 0: one real repeated root\n"
        "- D < 0: two complex conjugate roots.\n"
    )

    # Page 2: Differential Calculus
    p2 = doc.new_page()
    p2.insert_text(
        (50, 60),
        "2. Derivatives and Rules of Differentiation:\n"
        "The power rule states that d/dx [x^n] = n * x^(n-1).\n"
        "The derivative of a constant is zero: d/dx [c] = 0.\n"
        "Trigonometric derivatives:\n"
        "- d/dx [sin(x)] = cos(x)\n"
        "- d/dx [cos(x)] = -sin(x)\n"
        "- d/dx [tan(x)] = sec^2(x)\n"
        "Prerequisite Note: Mastering algebraic manipulation is required before evaluating calculus limits."
    )

    doc.save(file_path)
    doc.close()
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()

def create_biology_transcript(file_path: Path) -> str:
    text = (
        "[00:30] Welcome to Cellular Biology. Today we explore cell structure and primary organelles.\n"
        "[01:15] Cell Theory states that all living organisms are composed of one or more cells, and cells are the basic unit of life.\n"
        "[02:40] Mitochondria are double-membrane bound organelles known as the powerhouse of the cell, producing ATP via cellular respiration.\n"
        "[04:20] Chloroplasts in plant cells carry out photosynthesis, converting light energy and CO2 into glucose and oxygen.\n"
        "[05:50] The nucleus houses genetic material in the form of DNA chromatin fibers.\n"
    )
    file_path.write_text(text, encoding="utf-8")
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()

def build_reproducible_corpus(data_dir: Path) -> dict[str, str]:
    corpus_dir = data_dir / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    hashes: dict[str, str] = {}

    p_pdf = corpus_dir / "physics_mechanics.pdf"
    hashes["physics_mechanics"] = create_physics_pdf(p_pdf)

    o_pptx = corpus_dir / "waves_optics.pptx"
    hashes["waves_optics"] = create_optics_pptx(o_pptx)

    m_pdf = corpus_dir / "mathematics_calculus.pdf"
    hashes["mathematics_calculus"] = create_math_pdf(m_pdf)

    b_txt = corpus_dir / "biology_cell_lecture.txt"
    hashes["biology_cell_lecture"] = create_biology_transcript(b_txt)

    manifest = {
        "corpus_id": "cognivault-school-stem-benchmark-v1",
        "corpus_version": "1.0.0",
        "description": "Deterministic, reproducible School Mathematics and Science educational corpus fixtures created for CogniVault (Track D: Personalized Tutoring & Adaptive Learning).",
        "license": "CC0 1.0 Universal (Public Domain Dedication) / MIT License for project-authored synthetic test fixtures",
        "provenance_type": "project_authored_synthetic",
        "provenance_note": "Synthetic curriculum fixtures authored specifically for the CogniVault project, aligned with standard secondary school Mathematics (Algebra & Calculus), Physics (Classical Mechanics & Geometric Optics), and Biology (Cell Biology) educational benchmarks.",
        "parser_and_extractor_metadata": {
            "pdf_extractor": "PyMuPDF (fitz) v1.24+",
            "pptx_extractor": "python-pptx v1.0.2+",
            "transcript_extractor": "CogniVault Timestamped Regex Parser v1.0.0",
            "chunker_version": "CogniVault Hybrid Structure-Aware Chunker v1.0.0"
        },
        "sources": [
            {
                "source_id": "physics_mechanics",
                "title": "Classical Mechanics & Dynamics Textbook",
                "filename": "physics_mechanics.pdf",
                "subject": "Physics",
                "grade_level": "Secondary / High School",
                "modality": "pdf",
                "extractor": "pymupdf",
                "author": "CogniVault Project Team",
                "license": "CC0-1.0 (Public Domain Dedication)",
                "sha256": hashes["physics_mechanics"],
                "topics": ["Newtonian Mechanics", "Work and Energy"],
                "concepts": ["First Law", "Second Law", "Third Law", "Momentum", "Work", "Kinetic Energy"],
                "status": "verified"
            },
            {
                "source_id": "waves_optics",
                "title": "Wave Properties & Geometric Optics Lecture Slides",
                "filename": "waves_optics.pptx",
                "subject": "Physics",
                "grade_level": "Secondary / High School",
                "modality": "pptx",
                "extractor": "python-pptx",
                "author": "CogniVault Project Team",
                "license": "CC0-1.0 (Public Domain Dedication)",
                "sha256": hashes["waves_optics"],
                "topics": ["Wave Properties", "Geometric Optics"],
                "concepts": ["Wave Equation", "Reflection", "Snell's Law", "Refraction"],
                "status": "verified"
            },
            {
                "source_id": "mathematics_calculus",
                "title": "Algebra & Introductory Calculus Handbook",
                "filename": "mathematics_calculus.pdf",
                "subject": "Mathematics",
                "grade_level": "Secondary / High School",
                "modality": "pdf",
                "extractor": "pymupdf",
                "author": "CogniVault Project Team",
                "license": "CC0-1.0 (Public Domain Dedication)",
                "sha256": hashes["mathematics_calculus"],
                "topics": ["Algebra", "Differential Calculus"],
                "concepts": ["Quadratic Formula", "Discriminant", "Power Rule", "Trig Derivatives"],
                "status": "verified"
            },
            {
                "source_id": "biology_cell_lecture",
                "title": "Cell Biology Lecture Transcript",
                "filename": "biology_cell_lecture.txt",
                "subject": "Biology",
                "grade_level": "Secondary / High School",
                "modality": "text",
                "extractor": "regex-transcript",
                "author": "CogniVault Project Team",
                "license": "CC0-1.0 (Public Domain Dedication)",
                "sha256": hashes["biology_cell_lecture"],
                "topics": ["Cell Biology"],
                "concepts": ["Cell Theory", "Mitochondria", "Chloroplasts", "Nucleus"],
                "status": "verified"
            }
        ]
    }

    manifest_path = data_dir / "corpus_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return hashes

def seed_database_from_corpus(db: EvidenceDB, data_dir: Path | str | None = None) -> dict[str, int]:
    if data_dir is None:
        data_dir = Path("data")
    else:
        data_dir = Path(data_dir)

    corpus_dir = data_dir / "corpus"
    if not corpus_dir.exists():
        build_reproducible_corpus(data_dir)

    # 1. Ingest files
    ingest_pdf(corpus_dir / "physics_mechanics.pdf", db, source_id="physics_mechanics")
    ingest_pptx(corpus_dir / "waves_optics.pptx", db, source_id="waves_optics")
    ingest_pdf(corpus_dir / "mathematics_calculus.pdf", db, source_id="mathematics_calculus")
    ingest_transcript(corpus_dir / "biology_cell_lecture.txt", db, source_id="biology_cell_lecture")

    # 2. Register Topics and Concepts
    # Topics
    db.add_topic("Newtonian Mechanics", "Newtonian Mechanics", description="Forces and motion")
    db.add_topic("Work and Energy", "Work and Energy", description="Work, kinetic and potential energy")
    db.add_topic("Wave Properties", "Wave Properties", description="Wave speed, frequency, wavelength")
    db.add_topic("Geometric Optics", "Geometric Optics", description="Reflection and refraction")
    db.add_topic("Algebra", "Algebra", description="Polynomials and quadratic equations")
    db.add_topic("Differential Calculus", "Differential Calculus", description="Limits and derivatives")
    db.add_topic("Cell Biology", "Cell Biology", description="Cellular organelles and respiration")

    # Concepts & Prerequisites
    db.add_concept("Algebra", "Algebra", topic_id="Algebra")
    db.add_concept("Quadratic Formula", "Quadratic Formula", topic_id="Algebra")
    db.add_concept("Differential Calculus", "Differential Calculus", topic_id="Differential Calculus")
    db.add_concept("Power Rule", "Power Rule", topic_id="Differential Calculus")
    db.link_concept_prerequisite("Differential Calculus", "Algebra")
    db.link_concept_prerequisite("Power Rule", "Algebra")

    db.add_concept("Newtonian Mechanics", "Newtonian Mechanics", topic_id="Newtonian Mechanics")
    db.add_concept("Second Law", "Second Law", topic_id="Newtonian Mechanics")
    db.add_concept("Work and Energy", "Work and Energy", topic_id="Work and Energy")
    db.add_concept("Kinetic Energy", "Kinetic Energy", topic_id="Work and Energy")
    db.link_concept_prerequisite("Work and Energy", "Newtonian Mechanics")
    db.link_concept_prerequisite("Kinetic Energy", "Second Law")

    db.add_concept("Wave Properties", "Wave Properties", topic_id="Wave Properties")
    db.add_concept("Geometric Optics", "Geometric Optics", topic_id="Geometric Optics")
    db.link_concept_prerequisite("Geometric Optics", "Wave Properties")

    # 3. Seed verified questions for assessment engine
    engine = AssessmentEngine(db)

    # Question 1: Physics MCQ
    ev_physics = [e.evidence_id for e in db.get_evidence_for_topic("Newtonian Mechanics") or list(db.all_evidence())[:1]]
    engine.build_and_verify_question(
        question_id="q_seed_01",
        topic_id="Newtonian Mechanics",
        concept_id="Second Law",
        prompt="According to Newton's Second Law of Motion, what is the formula relating force, mass, and acceleration?",
        expected_answer="A",
        evidence_ids=ev_physics[:1],
        difficulty=Difficulty.easy,
        question_type=QuestionType.mcq,
        options=[
            QuestionOption(key="A", text="F = m * a"),
            QuestionOption(key="B", text="F = m / a"),
            QuestionOption(key="C", text="F = 0.5 * m * v^2"),
            QuestionOption(key="D", text="F = m * g * h")
        ],
        solution="Newton's second law is defined by Force = mass * acceleration (F = m * a)."
    )

    # Question 1b: Physics MCQ Alternative
    engine.build_and_verify_question(
        question_id="q_seed_01_alt",
        topic_id="Newtonian Mechanics",
        concept_id="Second Law",
        prompt="If a net force of 20 N is applied to a 5 kg object, what is its acceleration?",
        expected_answer="B",
        evidence_ids=ev_physics[:1],
        difficulty=Difficulty.medium,
        question_type=QuestionType.mcq,
        options=[
            QuestionOption(key="A", text="2 m/s^2"),
            QuestionOption(key="B", text="4 m/s^2"),
            QuestionOption(key="C", text="10 m/s^2"),
            QuestionOption(key="D", text="100 m/s^2")
        ],
        solution="Using a = F / m = 20 N / 5 kg = 4 m/s^2."
    )

    # Question 2: Physics Numerical
    engine.build_and_verify_question(
        question_id="q_seed_02",
        topic_id="Work and Energy",
        concept_id="Kinetic Energy",
        prompt="Calculate the kinetic energy in Joules of a 4.0 kg object moving at a velocity of 3.0 m/s (E_k = 0.5 * m * v^2).",
        expected_answer="18.0",
        evidence_ids=ev_physics[:1],
        difficulty=Difficulty.medium,
        question_type=QuestionType.numerical,
        tolerance=0.1,
        solution="E_k = 0.5 * 4.0 kg * (3.0 m/s)^2 = 0.5 * 4.0 * 9.0 = 18.0 Joules."
    )

    # Question 3: Mathematics MCQ
    ev_math = [e.evidence_id for e in db.get_evidence_for_topic("Algebra") or list(db.all_evidence())[:1]]
    engine.build_and_verify_question(
        question_id="q_seed_03",
        topic_id="Algebra",
        concept_id="Quadratic Formula",
        prompt="What is the quadratic formula used to solve ax^2 + bx + c = 0?",
        expected_answer="A",
        evidence_ids=ev_math[:1],
        difficulty=Difficulty.medium,
        question_type=QuestionType.mcq,
        options=[
            QuestionOption(key="A", text="x = (-b +- sqrt(b^2 - 4ac)) / (2a)"),
            QuestionOption(key="B", text="x = (-b +- sqrt(b^2 + 4ac)) / (2a)"),
            QuestionOption(key="C", text="x = (-b +- 4ac) / (2a)"),
            QuestionOption(key="D", text="x = (b +- sqrt(b^2 - 4ac)) / a")
        ],
        solution="The quadratic formula is x = (-b +- sqrt(b^2 - 4ac)) / (2a)."
    )

    # Question 4: Biology MCQ
    ev_bio = [e.evidence_id for e in db.get_evidence_for_topic("Cell Biology") or list(db.all_evidence())[:1]]
    engine.build_and_verify_question(
        question_id="q_seed_04",
        topic_id="Cell Biology",
        concept_id="Mitochondria",
        prompt="Which cellular organelle is responsible for producing ATP via cellular respiration?",
        expected_answer="B",
        evidence_ids=ev_bio[:1],
        difficulty=Difficulty.easy,
        question_type=QuestionType.mcq,
        options=[
            QuestionOption(key="A", text="Ribosome"),
            QuestionOption(key="B", text="Mitochondria"),
            QuestionOption(key="C", text="Endoplasmic Reticulum"),
            QuestionOption(key="D", text="Golgi Apparatus")
        ],
        solution="Mitochondria are the powerhouse of the cell, generating ATP through respiration."
    )

    # Question 5: Optics MCQ
    ev_optics = [e.evidence_id for e in db.get_evidence_for_topic("Geometric Optics") or list(db.all_evidence())[:1]]
    engine.build_and_verify_question(
        question_id="q_seed_05",
        topic_id="Geometric Optics",
        concept_id="Snell's Law",
        prompt="Which mathematical equation states Snell's law of refraction across media 1 and 2?",
        expected_answer="C",
        evidence_ids=ev_optics[:1],
        difficulty=Difficulty.medium,
        question_type=QuestionType.mcq,
        options=[
            QuestionOption(key="A", text="n1 * cos(theta1) = n2 * cos(theta2)"),
            QuestionOption(key="B", text="n1 / sin(theta1) = n2 / sin(theta2)"),
            QuestionOption(key="C", text="n1 * sin(theta1) = n2 * sin(theta2)"),
            QuestionOption(key="D", text="n1 * v1 = n2 * v2")
        ],
        solution="Snell's law is given by n1 * sin(theta1) = n2 * sin(theta2)."
    )

    stats = {
        "sources": len(db.all_sources()),
        "evidence_units": len(list(db.all_evidence())),
        "topics": len(db.all_topics()),
        "concepts": len(db.all_concepts()),
        "questions": len(db.all_questions())
    }
    return stats


def get_corpus_manifest(manifest_path: str | Path = "data/corpus_manifest.json") -> dict:
    """Retrieve corpus manifest metadata dict, generating or reading manifest file."""
    p = Path(manifest_path)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "corpus_id": "cognivault-school-math-science-v1",
        "version": "1.0.0",
        "description": "Deterministic baseline Mathematics and Science educational corpus.",
        "sources": []
    }


seed_corpus = seed_database_from_corpus


