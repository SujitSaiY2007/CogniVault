import io

import pytest

from app.corpus import build_all
from app.ingest import IngestError, parse_cues, parse_file
from app.nlp import sentences, specifier_terms, stem, term_set

CORPUS = build_all()


def test_stemmer_is_consistent_for_inflections():
    assert stem("refraction") == stem("refractions")
    assert term_set("Newton's laws") == term_set("newton law")


def test_sentences_split_on_lines_and_punctuation():
    assert sentences("Title line\nFirst sentence here. Second one follows.") == ["Title line", "First sentence here.", "Second one follows."]


def test_specifiers_capture_numbers_and_ordinals():
    assert specifier_terms("What is Newton's fourth law in 1994?") == {"fourth", "1994"}


def test_pdf_keeps_page_locators_sections_and_figures():
    p = parse_file(CORPUS["physics_mechanics.pdf"], "physics_mechanics.pdf", "s1")
    assert p.source.metadata["pages"] == 3
    pages = {u.location["page"] for u in p.units}
    assert pages == {1, 2, 3}
    sections = {u.section for u in p.units}
    assert "Newton's Second Law" in sections and "Linear Momentum" in sections
    figs = [u for u in p.units if u.evidence_type == "figure"]
    assert figs and "Free-body diagram" in figs[0].text and figs[0].location["page"] == 1
    assert p.assets and p.assets[0][2].startswith("image/")
    second = next(u for u in p.units if u.section == "Newton's Second Law" and u.evidence_type == "text")
    assert "F = m * a" in second.text


def test_pptx_slides_notes_and_alt_text():
    p = parse_file(CORPUS["waves_optics.pptx"], "waves_optics.pptx", "s2")
    slides = [u for u in p.units if u.evidence_type == "slide"]
    notes = [u for u in p.units if u.evidence_type == "notes"]
    assert len(slides) == 6 and len(notes) == 6
    assert notes[0].location == {"slide": 1, "part": "notes"}
    fig = next(u for u in p.units if u.evidence_type == "figure")
    assert fig.location["slide"] == 4 and "Ray diagram" in fig.text


def test_srt_vtt_and_bracket_transcripts_get_timestamps():
    p = parse_file(CORPUS["biology_cell_lecture.srt"], "bio.srt", "s3")
    assert all("timestamp" in u.location for u in p.units)
    assert p.units[0].location["timestamp"] == "00:00:12"
    vtt = b"WEBVTT\n\n00:01.000 --> 00:04.000\nHello <b>class</b>\n\n01:02:03.500 --> 01:02:09.000\nLater cue\n"
    cues = parse_cues(vtt.decode())
    assert cues[0] == (1.0, 4.0, "Hello class") and cues[1][0] == pytest.approx(3723.5)
    txt = b"[00:10] Intro to waves\n[01:20] Frequency is measured in hertz\n[02:30] Wavelength is a distance\n"
    t = parse_file(txt, "lecture.txt", "s4")
    assert t.source.modality.value == "video" and t.units[0].location["timestamp"] == "00:00:10"


def test_plain_notes_are_documents_not_transcripts():
    p = parse_file(b"# Cells\n\nA cell is the smallest unit of life.\n\nCells divide by mitosis.\n", "notes.md", "s5")
    assert p.source.modality.value == "text"
    assert p.units[0].location["section"] == "Cells"


@pytest.mark.parametrize(
    "data,name,msg",
    [
        (b"", "x.pdf", "empty"),
        (b"hello", "x.pdf", "does not look like a PDF"),
        (b"hello", "x.pptx", "does not look like"),
        (b"abc", "x.docx", "Unsupported file type"),
        (b"no timestamps at all", "x.srt", "No timestamps"),
    ],
)
def test_bad_files_fail_with_clear_messages(data, name, msg):
    with pytest.raises(IngestError, match=msg):
        parse_file(data, name, "bad")


def test_scanned_pdf_warns_instead_of_failing_silently():
    import pymupdf
    from PIL import Image

    img = Image.new("RGB", (400, 300), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(pymupdf.Rect(50, 50, 450, 350), stream=buf.getvalue())
    p = parse_file(doc.tobytes(), "scan.pdf", "scan")
    assert any("scanned" in w for w in p.warnings)
