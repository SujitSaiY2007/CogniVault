"""Bundled demo course (original, project-authored, CC0).

Four sources in four formats so every parser path is exercised:
  physics_mechanics.pdf      textbook chapter with headings, formulas and a figure
  waves_optics.pptx          lecture slides with speaker notes and a diagram
  mathematics_calculus.pdf   handbook pages on algebra and derivatives
  biology_cell_lecture.srt   timestamped lecture transcript

Files are generated deterministically if missing, so the repository can be
rebuilt from source.
"""
from __future__ import annotations

import io
from pathlib import Path

PHYSICS = [
    ("Classical Mechanics", [
        ("Newton's First Law", [
            "Newton's first law states that an object at rest stays at rest, and an object in motion keeps moving in a straight line at constant speed, unless a net external force acts on it.",
            "Inertia is the tendency of an object to resist changes in its state of motion. Objects with more mass have more inertia, so they are harder to start, stop or turn.",
            "A seatbelt works because of inertia: when a car brakes suddenly, the passenger's body tends to keep moving forward until the belt applies a force.",
        ]),
        ("Newton's Second Law", [
            "Newton's second law states that the acceleration of an object is directly proportional to the net force on it and inversely proportional to its mass. In equation form, F = m * a, where F is the net force in newtons (N), m is the mass in kilograms (kg), and a is the acceleration in metres per second squared (m/s^2).",
            "A newton is the force needed to accelerate a mass of one kilogram at one metre per second squared.",
            "Doubling the net force on an object doubles its acceleration, while doubling the mass halves the acceleration.",
        ]),
    ]),
    ("Forces in Pairs and Momentum", [
        ("Newton's Third Law", [
            "Newton's third law states that for every action force there is an equal and opposite reaction force. The two forces act on different objects, so they never cancel each other out.",
            "When you push against a wall, the wall pushes back on your hands with a force of the same size in the opposite direction.",
        ]),
        ("Linear Momentum", [
            "Momentum is the product of an object's mass and its velocity. It is written p = m * v, where p is the momentum in kilogram metres per second (kg m/s), m is the mass in kilograms (kg), and v is the velocity in metres per second (m/s).",
            "The law of conservation of momentum states that the total momentum of an isolated system stays constant during a collision or explosion.",
            "This section builds on Newton's second law, because a net force acting on an object changes its momentum.",
            "Impulse is the change in momentum of an object, equal to the net force multiplied by the time for which it acts.",
        ]),
    ]),
    ("Work and Energy", [
        ("Work", [
            "Work is the energy transferred when a force moves an object through a distance in the direction of the force. It is calculated as W = F * d, where W is the work in joules (J), F is the force in newtons (N), and d is the displacement in metres (m).",
            "Calculating work requires Newton's second law, because F in this formula is the net force on the object.",
            "No work is done when the force is perpendicular to the motion, for example when carrying a bag horizontally at constant height.",
        ]),
        ("Kinetic and Potential Energy", [
            "Kinetic energy is the energy an object has because of its motion. It is calculated as E_k = 0.5 * m * v^2, where E_k is the kinetic energy in joules (J), m is the mass in kilograms (kg), and v is the speed in metres per second (m/s).",
            "Gravitational potential energy is the energy stored in an object because of its height above a reference level. It is calculated as E_p = m * g * h, where E_p is the potential energy in joules (J), m is the mass in kilograms (kg), g is the gravitational field strength in newtons per kilogram (N/kg), and h is the height in metres (m).",
            "The work-energy principle states that the net work done on an object equals the change in its kinetic energy.",
        ]),
    ]),
]

MATH = [
    ("Algebra", [
        ("Quadratic Equations", [
            "A quadratic equation is an equation of the form ax^2 + bx + c = 0, where a, b and c are constants and a is not zero.",
            "The quadratic formula gives the roots of any quadratic equation: x = (-b +- sqrt(b^2 - 4ac)) / (2a).",
            "The discriminant is the expression b^2 - 4ac under the square root in the quadratic formula. If the discriminant is positive there are two distinct real roots, if it is zero there is one repeated real root, and if it is negative there are no real roots.",
        ]),
        ("Factorising", [
            "Factorising is the process of writing an expression as a product of simpler expressions. For example, x^2 - 5x + 6 can be factorised as (x - 2)(x - 3), so its roots are 2 and 3.",
            "The difference of two squares is the identity a^2 - b^2 = (a - b)(a + b).",
        ]),
    ]),
    ("Differential Calculus", [
        ("The Derivative", [
            "The derivative is the instantaneous rate of change of a function with respect to its input. Geometrically, it is the slope of the tangent line to the graph at a point.",
            "Factorising and simplifying fractions, covered in the algebra chapter, are needed before working with derivatives.",
        ]),
        ("Rules of Differentiation", [
            "The power rule states that the derivative of x^n is n * x^(n-1) for any real number n. For example, the derivative of x^3 is 3x^2.",
            "The constant rule states that the derivative of a constant is zero.",
            "The product rule states that the derivative of u * v is u' * v + u * v'.",
            "The chain rule states that the derivative of a composite function f(g(x)) is f'(g(x)) * g'(x).",
        ]),
    ]),
]

SLIDES = [
    ("Wave Basics", ["A wave is a disturbance that transfers energy from one place to another without transferring matter.",
                     "Wavelength is the distance between two consecutive crests of a wave, measured in metres (m).",
                     "Frequency is the number of waves passing a point each second, measured in hertz (Hz)."],
     "Start with a rope or slinky demo. Stress that the medium does not travel with the wave."),
    ("The Wave Equation", ["The wave equation relates speed, frequency and wavelength: v = f * lambda",
                           "where v is the wave speed in metres per second (m/s), f is the frequency in hertz (Hz), and lambda is the wavelength in metres (m).",
                           "The period is the time for one complete wave: T = 1 / f"],
     "Frequency is set by the source and stays the same when a wave enters a new medium; speed and wavelength change."),
    ("Reflection", ["The law of reflection states that the angle of incidence equals the angle of reflection.",
                    "Both angles are measured from the normal, an imaginary line perpendicular to the surface."],
     "Use a plane mirror and a ray box to show equal angles."),
    ("Refraction and Snell's Law", ["Refraction is the change in direction of a wave as it passes from one medium into another and its speed changes.",
                                    "Snell's law states that n1 * sin(theta1) = n2 * sin(theta2) at the boundary between two media.",
                                    "Refraction builds on the wave equation: when the wave speed changes, the wavelength changes too."],
     "Light bends towards the normal when it slows down, for example from air into glass."),
    ("Refractive Index", ["The refractive index of a medium is the ratio of the speed of light in a vacuum to the speed of light in the medium: n = c / v",
                          "where c is the speed of light in a vacuum in metres per second (m/s) and v is the speed of light in the medium in metres per second (m/s)."],
     "Water has a refractive index of about 1.33 and glass about 1.5."),
    ("Total Internal Reflection", ["Total internal reflection happens when light travelling in a denser medium hits the boundary at an angle greater than the critical angle, so all of it is reflected.",
                                   "Optical fibres use total internal reflection to carry light signals over long distances.",
                                   "This idea builds on Snell's law and the refractive index of a medium."],
     "Link back to Snell's law: beyond the critical angle there is no refracted ray."),
]

TRANSCRIPT = [
    (12, "Welcome to today's lecture on cell biology. We are going to look at what cells are made of and what each part does."),
    (31, "Cell theory states that all living things are made of one or more cells, that the cell is the basic unit of life, and that new cells come from existing cells."),
    (58, "There are two broad kinds of cell. Prokaryotic cells, such as bacteria, have no nucleus. Eukaryotic cells, such as plant and animal cells, keep their DNA inside a nucleus."),
    (95, "The cell membrane is a thin, flexible barrier that controls which substances enter and leave the cell. It is partially permeable."),
    (131, "The nucleus is the control centre of a eukaryotic cell. It contains the genetic material, DNA, which carries the instructions for making proteins."),
    (170, "Mitochondria are organelles where aerobic respiration takes place. They release energy from glucose and store it as ATP, which is why they are called the powerhouse of the cell."),
    (214, "ATP, adenosine triphosphate, is the molecule cells use to carry energy to the processes that need it, such as muscle contraction and active transport."),
    (252, "Chloroplasts are found in plant cells and some algae. They contain chlorophyll, which absorbs light energy for photosynthesis."),
    (289, "Photosynthesis is the process in which plants use light energy to convert carbon dioxide and water into glucose and oxygen."),
    (331, "Ribosomes are small structures where proteins are made, following the instructions copied from DNA."),
    (366, "Plant cells also have a cell wall made of cellulose, which gives the cell strength and support, and a large vacuole filled with cell sap."),
    (402, "To summarise: the membrane controls entry and exit, the nucleus stores DNA, mitochondria release energy as ATP, and chloroplasts carry out photosynthesis."),
]


def _diagram_png(kind: str) -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (320, 220), (255, 255, 255))
    d = ImageDraw.Draw(img)
    if kind == "fbd":
        d.rectangle([120, 80, 200, 140], outline=(0, 0, 0), width=3)
        for (x0, y0, x1, y1) in [(160, 80, 160, 20), (160, 140, 160, 200), (200, 110, 290, 110), (120, 110, 40, 110)]:
            d.line([x0, y0, x1, y1], fill=(0, 0, 0), width=3)
        d.text((165, 15), "Normal force", fill=(0, 0, 0))
        d.text((165, 195), "Weight", fill=(0, 0, 0))
        d.text((230, 95), "Push", fill=(0, 0, 0))
        d.text((40, 95), "Friction", fill=(0, 0, 0))
    else:
        d.line([20, 110, 300, 110], fill=(0, 0, 0), width=2)
        d.line([60, 20, 160, 110], fill=(0, 0, 0), width=3)
        d.line([160, 110, 230, 210], fill=(0, 0, 0), width=3)
        d.line([160, 20, 160, 210], fill=(120, 120, 120), width=1)
        d.text((30, 90), "air (n1)", fill=(0, 0, 0))
        d.text((30, 120), "glass (n2)", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _pdf(chapters, title: str, figure: tuple[int, str] | None = None) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    for ci, (chapter, sections) in enumerate(chapters, 1):
        page = doc.new_page()
        y = 60
        page.insert_text((50, y), f"{ci}. {chapter}", fontsize=18, fontname="hebo")
        y += 34
        for sec, paras in sections:
            page.insert_text((50, y), sec, fontsize=13.5, fontname="hebo")
            y += 22
            for para in paras:
                rect = pymupdf.Rect(50, y, 545, y + 200)
                h = page.insert_textbox(rect, para, fontsize=10.5, fontname="helv")
                used = 200 - h if h >= 0 else 200
                y += used + 10
            y += 6
        if figure and figure[0] == ci:
            page.insert_image(pymupdf.Rect(50, y, 290, y + 165), stream=_diagram_png("fbd"))
            page.insert_text((50, y + 182), figure[1], fontsize=9.5, fontname="helv")
    doc.set_metadata({"title": title, "author": "CogniVault demo course (CC0)"})
    data = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return data


def _pptx() -> bytes:
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()
    for i, (title, bullets, notes) in enumerate(SLIDES):
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = title
        tf = s.placeholders[1].text_frame
        tf.text = bullets[0]
        for b in bullets[1:]:
            p = tf.add_paragraph()
            p.text = b
            p.font.size = Pt(18)
        s.notes_slide.notes_text_frame.text = notes
        if title.startswith("Refraction"):
            pic = s.shapes.add_picture(io.BytesIO(_diagram_png("ray")), Inches(6.2), Inches(4.6), width=Inches(3.2))
            pic._element.nvPicPr.cNvPr.set("descr", "Ray diagram: light bending towards the normal as it passes from air (n1) into glass (n2)")
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _srt() -> bytes:
    def ts(s: float) -> str:
        return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},000"

    out = []
    for i, (start, text) in enumerate(TRANSCRIPT, 1):
        end = TRANSCRIPT[i][0] - 1 if i < len(TRANSCRIPT) else start + 30
        out.append(f"{i}\n{ts(start)} --> {ts(end)}\n{text}\n")
    return "\n".join(out).encode("utf-8")


def build_all() -> dict[str, bytes]:
    return {
        "physics_mechanics.pdf": _pdf(PHYSICS, "Classical Mechanics", (1, "Figure 1: Free-body diagram of a box being pushed, showing the normal force, weight, push and friction.")),
        "waves_optics.pptx": _pptx(),
        "mathematics_calculus.pdf": _pdf(MATH, "Algebra and Calculus"),
        "biology_cell_lecture.srt": _srt(),
    }


DEMO_TITLES = {
    "physics_mechanics.pdf": "Classical Mechanics (textbook)",
    "waves_optics.pptx": "Waves and Optics (lecture slides)",
    "mathematics_calculus.pdf": "Algebra and Calculus (handbook)",
    "biology_cell_lecture.srt": "Cell Biology (lecture video transcript)",
}


def ensure_corpus(corpus_dir: Path) -> list[Path]:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    names = ["physics_mechanics.pdf", "waves_optics.pptx", "mathematics_calculus.pdf", "biology_cell_lecture.srt"]
    if not all((corpus_dir / n).exists() for n in names):
        for name, data in build_all().items():
            (corpus_dir / name).write_bytes(data)
    return [corpus_dir / n for n in names]
