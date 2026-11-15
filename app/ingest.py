"""Parse course files into addressable evidence units.

Supported: PDF (text, headings, figures with captions), PPTX (slide text,
tables, speaker notes, pictures), lecture transcripts (.srt, .vtt, and
timestamped .txt), and plain notes (.txt, .md).

Every unit keeps an exact locator: page, slide, timestamp, or section.
Parsers are pure functions: they return a ``ParsedSource`` and never touch
the database.
"""
from __future__ import annotations

import hashlib
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .models import PUBLIC_OWNER, EvidenceUnit, Modality, SourceRecord
from .nlp import normalize, sentences, word_count

SUPPORTED_EXTENSIONS = {".pdf", ".pptx", ".srt", ".vtt", ".txt", ".md"}
TARGET_WORDS = 140   # soft target per text chunk
MAX_WORDS = 230      # hard cap per text chunk
MIN_IMAGE_PX = 80    # ignore icons, bullets and rules

_FIG_RE = re.compile(r"^\s*(fig(?:ure)?\.?\s*\d+(?:[.\-]\d+)*)\s*[:.\-–]?\s*(.*)$", re.I)
_NUM_HEADING_RE = re.compile(r"^\s*(?:chapter\s+\d+|\d+(?:\.\d+){0,3})[.)]?\s+[A-Z][^.!?]{2,90}$")


class IngestError(ValueError):
    """Raised for files that cannot be parsed. Message is safe to show users."""


@dataclass
class ParsedSource:
    source: SourceRecord
    units: list[EvidenceUnit]
    assets: list[tuple[str, str, str, bytes]] = field(default_factory=list)  # (asset_id, evidence_id, mime, data)
    warnings: list[str] = field(default_factory=list)
    headings: list[tuple[str, dict[str, Any]]] = field(default_factory=list)  # (heading, first locator)


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def locator_label(location: dict[str, Any]) -> str:
    if "page" in location:
        return f"Page {location['page']}"
    if "slide" in location:
        return f"Slide {location['slide']}" + (" (speaker notes)" if location.get("part") == "notes" else "")
    if "timestamp" in location:
        return str(location["timestamp"])
    if "section" in location:
        para = location.get("paragraph")
        return f"{location['section']}" + (f", para {para}" if para else "")
    return "Course material"


class _Builder:
    def __init__(self, source_id: str, owner_id: str, modality: Modality):
        self.source_id, self.owner_id, self.modality = source_id, owner_id, modality
        self.units: list[EvidenceUnit] = []
        self.assets: list[tuple[str, str, str, bytes]] = []

    def next_id(self) -> str:
        return f"{self.source_id}:e{len(self.units) + 1:04d}"

    def add(self, text: str, location: dict[str, Any], kind: str = "text", section: str = "",
            modality: Optional[Modality] = None, metadata: Optional[dict[str, Any]] = None) -> EvidenceUnit:
        unit = EvidenceUnit(
            evidence_id=self.next_id(), source_id=self.source_id, owner_id=self.owner_id,
            modality=modality or self.modality, text=text.strip(), location=location, evidence_type=kind,
            section=section, metadata=metadata or {},
        )
        self.units.append(unit)
        return unit


def _chunk_paragraphs(paragraphs: list[str]) -> list[str]:
    """Greedy packing of paragraphs into chunks near TARGET_WORDS, never above MAX_WORDS."""
    chunks: list[str] = []
    cur: list[str] = []
    cur_words = 0
    for para in paragraphs:
        n = word_count(para)
        if n > MAX_WORDS:
            if cur:
                chunks.append("\n".join(cur))
                cur, cur_words = [], 0
            buf: list[str] = []
            bw = 0
            for s in sentences(para):
                sw = word_count(s)
                if buf and bw + sw > TARGET_WORDS:
                    chunks.append(" ".join(buf))
                    buf, bw = [], 0
                buf.append(s)
                bw += sw
            if buf:
                chunks.append(" ".join(buf))
            continue
        if cur and cur_words + n > TARGET_WORDS:
            chunks.append("\n".join(cur))
            cur, cur_words = [], 0
        cur.append(para)
        cur_words += n
    if cur:
        chunks.append("\n".join(cur))
    return [c for c in chunks if word_count(c) >= 3]


# ---------------------------------------------------------------------- PDF
def parse_pdf(data: bytes, source_id: str, title: str, owner_id: str = PUBLIC_OWNER, filename: str = "") -> ParsedSource:
    import pymupdf

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # pragma: no cover - depends on file
        raise IngestError("This PDF could not be opened. It may be corrupted or password protected.") from exc
    if doc.needs_pass:
        raise IngestError("This PDF is password protected. Remove the password and upload it again.")

    b = _Builder(source_id, owner_id, Modality.pdf)
    warnings: list[str] = []
    headings: list[tuple[str, dict[str, Any]]] = []

    # Pass 1: body font size = most common size weighted by characters.
    size_hist: Counter = Counter()
    pages_lines: list[list[dict[str, Any]]] = []
    for page in doc:
        lines: list[dict[str, Any]] = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
                if not spans:
                    continue
                text = normalize("".join(s["text"] for s in spans)).strip()
                size = max(s["size"] for s in spans)
                bold = all((s.get("flags", 0) & 16) or "bold" in s.get("font", "").lower() for s in spans)
                for s in spans:
                    size_hist[round(s["size"], 1)] += len(s["text"])
                lines.append({"text": text, "size": size, "bold": bold, "bbox": line["bbox"], "block": id(block)})
        pages_lines.append(lines)
    body_size = size_hist.most_common(1)[0][0] if size_hist else 11.0

    # Images that repeat on many pages are logos/headers: skip them.
    xref_pages: Counter = Counter()
    for page in doc:
        for img in {i[0] for i in page.get_images(full=True)}:
            xref_pages[img] += 1
    repeated = {x for x, c in xref_pages.items() if c >= max(3, int(0.5 * len(doc)))}

    section = title
    empty_pages = 0
    for page_no, (page, lines) in enumerate(zip(doc, pages_lines), 1):
        paragraphs: list[tuple[str, str]] = []  # (section, text)
        cur: list[str] = []
        last_block = None
        captions: list[tuple[str, tuple]] = []

        def flush():
            nonlocal cur
            if cur:
                paragraphs.append((section, " ".join(cur)))
            cur = []

        for ln in lines:
            text = ln["text"]
            if _FIG_RE.match(text):
                flush()
                captions.append((text, tuple(ln["bbox"])))
                continue
            words = word_count(text)
            is_heading = (
                words <= 14 and not text.endswith((".", ",", ";"))
                and (ln["size"] >= body_size * 1.15 or (ln["bold"] and words <= 10) or _NUM_HEADING_RE.match(text))
            )
            if is_heading:
                flush()
                section = re.sub(r"\s+", " ", text).strip(" :")
                headings.append((section, {"page": page_no}))
                last_block = ln["block"]
                continue
            if ln["block"] != last_block:
                flush()
                last_block = ln["block"]
            # Re-join words hyphenated across line breaks.
            if cur and cur[-1].endswith("-") and text[:1].islower():
                cur[-1] = cur[-1][:-1] + text
            else:
                cur.append(text)
        flush()

        # Group consecutive paragraphs of the same section, then chunk.
        groups: list[tuple[str, list[str]]] = []
        for sec, para in paragraphs:
            if groups and groups[-1][0] == sec:
                groups[-1][1].append(para)
            else:
                groups.append((sec, [para]))
        page_text_words = 0
        for sec, paras in groups:
            for chunk in _chunk_paragraphs(paras):
                page_text_words += word_count(chunk)
                b.add(chunk, {"page": page_no}, kind="text", section=sec)

        # Figures
        used_captions: set[str] = set()
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in repeated:
                continue
            try:
                info = doc.extract_image(xref)
            except Exception:
                continue
            w, h = info.get("width", 0), info.get("height", 0)
            if w < MIN_IMAGE_PX or h < MIN_IMAGE_PX:
                continue
            rects = page.get_image_rects(xref) or []
            caption = _nearest_caption(captions, rects[0] if rects else None)
            if caption:
                used_captions.add(caption)
            else:
                caption = _text_near_rect(lines, rects[0] if rects else None)
            fig_text = f"Figure on page {page_no}" + (f": {caption}" if caption else "")
            ext = info.get("ext", "png")
            unit = b.add(fig_text, {"page": page_no, "figure": len([u for u in b.units if u.evidence_type == 'figure']) + 1},
                         kind="figure", section=section, modality=Modality.image,
                         metadata={"caption": caption, "width": w, "height": h, "mime_type": f"image/{ext}"})
            asset_id = "asset:" + hashlib.sha256(info["image"]).hexdigest()[:24]
            unit.metadata["asset_id"] = asset_id
            b.assets.append((asset_id, unit.evidence_id, f"image/{ext}", info["image"]))

        # Captions without an extractable bitmap (vector drawings) are still evidence.
        for cap_text, _ in captions:
            cap = _cap_str(cap_text)
            if cap not in used_captions:
                b.add(f"Figure on page {page_no}: {cap}", {"page": page_no}, kind="figure", section=section,
                      modality=Modality.image, metadata={"caption": cap, "vector": True})

        if page_text_words == 0:
            empty_pages += 1

    if empty_pages and empty_pages == len(doc):
        warnings.append("No selectable text was found. This looks like a scanned PDF; text inside images is only read when a vision model is configured.")
    elif empty_pages:
        warnings.append(f"{empty_pages} page(s) had no selectable text.")
    src = SourceRecord(source_id=source_id, owner_id=owner_id, title=title, modality=Modality.pdf, path=filename,
                       sha256=file_sha256(data), metadata={"pages": len(doc), "filename": filename})
    doc.close()
    return ParsedSource(src, b.units, b.assets, warnings, headings)


def _cap_str(text: str) -> str:
    m = _FIG_RE.match(text)
    return (m.group(1) + ": " + m.group(2)).strip(": ") if m else text.strip()


def _nearest_caption(captions: list[tuple[str, tuple]], rect) -> str:
    if not captions:
        return ""
    if rect is None:
        return _cap_str(captions[0][0])
    cx, cy = (rect.x0 + rect.x1) / 2, rect.y1

    def dist(c):
        x0, y0, x1, y1 = c[1]
        return abs(y0 - cy) + 0.2 * abs((x0 + x1) / 2 - cx)

    return _cap_str(min(captions, key=dist)[0])


def _text_near_rect(lines: list[dict[str, Any]], rect) -> str:
    if rect is None:
        return ""
    below = [ln for ln in lines if 0 <= ln["bbox"][1] - rect.y1 <= 40 and word_count(ln["text"]) >= 3]
    return below[0]["text"] if below else ""


# --------------------------------------------------------------------- PPTX
def parse_pptx(data: bytes, source_id: str, title: str, owner_id: str = PUBLIC_OWNER, filename: str = "") -> ParsedSource:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    try:
        prs = Presentation(io.BytesIO(data))
    except Exception as exc:
        raise IngestError("This PowerPoint file could not be opened. Save it as .pptx and try again.") from exc

    b = _Builder(source_id, owner_id, Modality.pptx)
    headings: list[tuple[str, dict[str, Any]]] = []

    def walk(shapes):
        for sh in shapes:
            if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
                yield from walk(sh.shapes)
            else:
                yield sh

    for slide_no, slide in enumerate(prs.slides, 1):
        slide_title = ""
        if slide.shapes.title is not None and slide.shapes.title.has_text_frame:
            slide_title = normalize(slide.shapes.title.text_frame.text).strip()
        body: list[str] = []
        pictures = []
        for sh in walk(slide.shapes):
            if slide.shapes.title is not None and sh.shape_id == slide.shapes.title.shape_id:
                continue
            if getattr(sh, "has_text_frame", False) and sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    t = normalize("".join(r.text for r in p.runs)).strip()
                    if t:
                        body.append(("- " * min(p.level, 2)) + t if p.level else t)
            elif getattr(sh, "has_table", False) and sh.has_table:
                for row in sh.table.rows:
                    cells = [normalize(c.text).strip() for c in row.cells]
                    if any(cells):
                        body.append(" | ".join(cells))
            elif sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                pictures.append(sh)
        section = slide_title or f"Slide {slide_no}"
        if slide_title:
            headings.append((slide_title, {"slide": slide_no}))
        text = "\n".join(([slide_title] if slide_title else []) + body)
        if word_count(text) >= 2:
            b.add(text, {"slide": slide_no}, kind="slide", section=section)
        if slide.has_notes_slide:
            notes = normalize(slide.notes_slide.notes_text_frame.text if slide.notes_slide.notes_text_frame else "").strip()
            if word_count(notes) >= 3:
                b.add(notes, {"slide": slide_no, "part": "notes"}, kind="notes", section=section)
        for pic in pictures:
            try:
                blob, ctype = pic.image.blob, pic.image.content_type
            except Exception:
                continue
            try:
                from PIL import Image
                w, h = Image.open(io.BytesIO(blob)).size
            except Exception:
                w = h = MIN_IMAGE_PX
            if w < MIN_IMAGE_PX or h < MIN_IMAGE_PX:
                continue
            alt = ""
            try:
                alt = pic._element.nvPicPr.cNvPr.get("descr") or ""
            except Exception:
                pass
            caption = alt or slide_title
            unit = b.add(f"Figure on slide {slide_no}" + (f": {caption}" if caption else ""), {"slide": slide_no},
                         kind="figure", section=section, modality=Modality.image,
                         metadata={"caption": caption, "width": w, "height": h, "mime_type": ctype})
            asset_id = "asset:" + hashlib.sha256(blob).hexdigest()[:24]
            unit.metadata["asset_id"] = asset_id
            b.assets.append((asset_id, unit.evidence_id, ctype, blob))

    src = SourceRecord(source_id=source_id, owner_id=owner_id, title=title, modality=Modality.pptx, path=filename,
                       sha256=file_sha256(data), metadata={"slides": len(prs.slides), "filename": filename})
    warnings = [] if b.units else ["No readable text was found on any slide."]
    return ParsedSource(src, b.units, b.assets, warnings, headings)


# --------------------------------------------------------------- transcripts
_SRT_TIME = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")
_VTT_TIME = re.compile(r"((?:\d{1,2}:)?\d{1,2}:\d{2}(?:\.\d{1,3})?)\s*-->\s*((?:\d{1,2}:)?\d{1,2}:\d{2}(?:\.\d{1,3})?)")
_LINE_TS = re.compile(r"^\s*[\[(]?((?:\d{1,2}:)?\d{1,2}:\d{2})[\])]?\s*[-:–]?\s+(.+)$")


def _to_seconds(ts: str) -> float:
    parts = [float(p) for p in ts.replace(",", ".").split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def parse_cues(text: str) -> list[tuple[float, float, str]]:
    """Return (start, end, text) cues from SRT, WebVTT or '[mm:ss] text' lines."""
    text = normalize(text).replace("\r\n", "\n")
    cues: list[tuple[float, float, str]] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = _SRT_TIME.search(line) or _VTT_TIME.search(line)
        if m and "-->" in line:
            if m.re is _SRT_TIME:
                g = m.groups()
                start = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
                end = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
            else:
                start, end = _to_seconds(m.group(1)), _to_seconds(m.group(2))
            i += 1
            body = []
            while i < len(lines) and lines[i].strip() and "-->" not in lines[i]:
                body.append(re.sub(r"<[^>]+>", "", lines[i]).strip())
                i += 1
            t = " ".join(x for x in body if x and not x.isdigit())
            if t:
                cues.append((start, end, t))
            continue
        m2 = _LINE_TS.match(line)
        if m2:
            start = _to_seconds(m2.group(1))
            if cues and cues[-1][1] == cues[-1][0]:
                s0, _, t0 = cues[-1]
                cues[-1] = (s0, start, t0)
            cues.append((start, start, m2.group(2).strip()))
        i += 1
    return cues


def looks_like_transcript(text: str) -> bool:
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return False
    if text.lstrip().startswith("WEBVTT") or "-->" in text:
        return True
    stamped = sum(1 for l in lines if _LINE_TS.match(l))
    return stamped >= max(2, int(0.3 * len(lines)))


def parse_transcript(data: bytes, source_id: str, title: str, owner_id: str = PUBLIC_OWNER, filename: str = "",
                     window_seconds: float = 60.0) -> ParsedSource:
    text = _decode(data)
    cues = parse_cues(text)
    if not cues:
        raise IngestError("No timestamps were found. Use .srt, .vtt, or lines starting with [mm:ss].")
    b = _Builder(source_id, owner_id, Modality.video)
    win: list[tuple[float, float, str]] = []

    def flush():
        if not win:
            return
        start, end = win[0][0], max(win[-1][1], win[-1][0])
        body = " ".join(c[2] for c in win)
        b.add(body, {"timestamp": fmt_ts(start), "start_seconds": round(start, 2), "end": fmt_ts(end)},
              kind="transcript", section=title)
        win.clear()

    for cue in cues:
        if win and (cue[0] - win[0][0] >= window_seconds or word_count(" ".join(c[2] for c in win)) >= TARGET_WORDS):
            flush()
        win.append(cue)
    flush()
    duration = max(c[1] for c in cues)
    src = SourceRecord(source_id=source_id, owner_id=owner_id, title=title, modality=Modality.video, path=filename,
                       sha256=file_sha256(data), metadata={"duration": fmt_ts(duration), "cues": len(cues), "filename": filename})
    return ParsedSource(src, b.units, [], [], [])


# -------------------------------------------------------------------- notes
_MD_HEADING = re.compile(r"^\s*#{1,6}\s+(.+?)\s*#*\s*$")


def parse_notes(data: bytes, source_id: str, title: str, owner_id: str = PUBLIC_OWNER, filename: str = "") -> ParsedSource:
    text = _decode(data)
    if looks_like_transcript(text):
        return parse_transcript(data, source_id, title, owner_id, filename)
    b = _Builder(source_id, owner_id, Modality.text)
    headings: list[tuple[str, dict[str, Any]]] = []
    section = title
    paras: list[str] = []
    cur: list[str] = []
    para_no = 0

    def flush_para():
        nonlocal cur
        if cur:
            paras.append(" ".join(cur))
        cur = []

    def flush_section():
        nonlocal para_no
        flush_para()
        for chunk in _chunk_paragraphs(paras):
            para_no += 1
            b.add(chunk, {"section": section, "paragraph": para_no}, kind="text", section=section)
        paras.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        m = _MD_HEADING.match(line)
        stripped = line.strip()
        is_heading = bool(m) or (
            stripped and word_count(stripped) <= 10 and not stripped.endswith((".", ",", ";", ":"))
            and (_NUM_HEADING_RE.match(stripped) or (stripped.isupper() and len(stripped) > 3))
        )
        if is_heading:
            flush_section()
            section = (m.group(1) if m else stripped).strip()
            para_no = 0
            headings.append((section, {"section": section}))
        elif not stripped:
            flush_para()
        else:
            cur.append(stripped.lstrip("*-• ").strip() if stripped[:1] in "*-•" else stripped)
    flush_section()
    if not b.units:
        raise IngestError("The file has no readable text.")
    src = SourceRecord(source_id=source_id, owner_id=owner_id, title=title, modality=Modality.text, path=filename,
                       sha256=file_sha256(data), metadata={"filename": filename})
    return ParsedSource(src, b.units, [], [], headings)


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            if enc == "utf-16" and "\x00" in text:
                continue
            return text
        except UnicodeDecodeError:
            continue
    raise IngestError("The text encoding of this file could not be read.")


def parse_file(data: bytes, filename: str, source_id: str, title: Optional[str] = None,
               owner_id: str = PUBLIC_OWNER) -> ParsedSource:
    ext = Path(filename).suffix.lower()
    if not title:
        stem_name = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
        title = stem_name[:1].upper() + stem_name[1:] if stem_name.islower() else stem_name
    title = title.strip() or "Untitled"
    if ext not in SUPPORTED_EXTENSIONS:
        raise IngestError(f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.")
    if not data:
        raise IngestError("The file is empty.")
    if ext == ".pdf":
        if not data.startswith(b"%PDF"):
            raise IngestError("This file does not look like a PDF.")
        parsed = parse_pdf(data, source_id, title, owner_id, filename)
    elif ext == ".pptx":
        if not data.startswith(b"PK"):
            raise IngestError("This file does not look like a .pptx file.")
        parsed = parse_pptx(data, source_id, title, owner_id, filename)
    elif ext in {".srt", ".vtt"}:
        parsed = parse_transcript(data, source_id, title, owner_id, filename)
    else:
        parsed = parse_notes(data, source_id, title, owner_id, filename)
    if not parsed.units:
        raise IngestError("No usable content was extracted from this file. " + " ".join(parsed.warnings))
    return parsed
