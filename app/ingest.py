from __future__ import annotations
import hashlib
import re
from pathlib import Path
from .db import EvidenceDB
from .models import EvidenceUnit, Modality, SourceRecord

TIMESTAMP_REGEX = re.compile(
    r"^\s*\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[:-]?\s*(.+)$"
)

def _sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def _bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _id(s: str, n: int) -> str:
    return f"{s}:e{n:05d}"

def _asset_id(data: bytes) -> str:
    return "asset:" + _bytes_sha256(data)[:24]

def _mime_from_ext(ext: str) -> str:
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "webp": "image/webp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
    }.get(ext.lower().lstrip("."), "application/octet-stream")

def _add_image_evidence(db: EvidenceDB, sid: str, eid: str, parent_modality: Modality, location: dict, data: bytes, mime_type: str, width: int | None = None, height: int | None = None):
    digest = _bytes_sha256(data)
    aid = _asset_id(data)
    db.add_evidence(
        EvidenceUnit(
            evidence_id=eid,
            source_id=sid,
            modality=Modality.image,
            text="Embedded figure/image evidence",
            location=location,
            evidence_type="image",
            asset_id=aid,
            metadata={
                "mime_type": mime_type,
                "sha256": digest,
                "parent_modality": parent_modality.value,
            }
        )
    )
    db.add_asset(aid, eid, mime_type, digest, data, width, height)

def ingest_pdf(path: str | Path, db: EvidenceDB, source_id: str | None = None) -> str:
    import pymupdf
    p = Path(path)
    file_sha = _sha256(p)
    sid = source_id or file_sha[:16]
    doc = pymupdf.open(p)
    db.add_source(
        SourceRecord(
            source_id=sid,
            path=str(p),
            modality=Modality.pdf,
            title=p.stem,
            sha256=file_sha
        )
    )
    n = 0
    for page_no, page in enumerate(doc, 1):
        text = page.get_text("text").strip()
        if text:
            raw_chunks = re.split(r"\n\s*\n", text)
            chunks = [c.strip() for c in raw_chunks if len(c.strip()) >= 5]
            if not chunks and text:
                chunks = [text]
            for chunk in chunks:
                n += 1
                db.add_evidence(
                    EvidenceUnit(
                        evidence_id=_id(sid, n),
                        source_id=sid,
                        modality=Modality.pdf,
                        text=chunk,
                        location={"page": page_no}
                    )
                )
        for img in page.get_images(full=True):
            xref = img[0]
            extracted = doc.extract_image(xref)
            data = extracted["image"]
            n += 1
            _add_image_evidence(
                db,
                sid,
                _id(sid, n),
                Modality.pdf,
                {"page": page_no, "image_xref": xref},
                data,
                _mime_from_ext(extracted["ext"]),
                extracted.get("width"),
                extracted.get("height")
            )
    return sid

def ingest_pptx(path: str | Path, db: EvidenceDB, source_id: str | None = None) -> str:
    from pptx import Presentation
    p = Path(path)
    file_sha = _sha256(p)
    sid = source_id or file_sha[:16]
    prs = Presentation(p)
    db.add_source(
        SourceRecord(
            source_id=sid,
            path=str(p),
            modality=Modality.pptx,
            title=p.stem,
            sha256=file_sha
        )
    )
    n = 0
    for slide_no, slide in enumerate(prs.slides, 1):
        texts = [sh.text.strip() for sh in slide.shapes if hasattr(sh, "text_frame") and sh.text.strip()]
        if texts:
            n += 1
            db.add_evidence(
                EvidenceUnit(
                    evidence_id=_id(sid, n),
                    source_id=sid,
                    modality=Modality.pptx,
                    text="\n".join(texts),
                    location={"slide": slide_no}
                )
            )
        for shape in slide.shapes:
            if shape.shape_type == 13:
                image = shape.image
                data = image.blob
                n += 1
                _add_image_evidence(
                    db,
                    sid,
                    _id(sid, n),
                    Modality.pptx,
                    {"slide": slide_no, "shape_id": shape.shape_id},
                    data,
                    image.content_type,
                    shape.width,
                    shape.height
                )
    return sid

def ingest_transcript(path: str | Path, db: EvidenceDB, source_id: str | None = None) -> str:
    p = Path(path)
    file_sha = _sha256(p)
    sid = source_id or file_sha[:16]
    db.add_source(
        SourceRecord(
            source_id=sid,
            path=str(p),
            modality=Modality.video,
            title=p.stem,
            sha256=file_sha
        )
    )
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        m = TIMESTAMP_REGEX.match(line_clean)
        if m:
            text = m.group(2).strip()
            if text:
                n += 1
                db.add_evidence(
                    EvidenceUnit(
                        evidence_id=_id(sid, n),
                        source_id=sid,
                        modality=Modality.video,
                        text=text,
                        location={"timestamp": m.group(1)}
                    )
                )
    return sid

def ingest_file(path: str | Path, db: EvidenceDB, source_id: str | None = None) -> str:
    """Convenience dispatcher to ingest PDF, PPTX, or transcript file by extension."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        return ingest_pdf(p, db, source_id=source_id)
    elif ext in {".pptx", ".ppt"}:
        return ingest_pptx(p, db, source_id=source_id)
    elif ext in {".txt", ".vtt", ".srt"}:
        return ingest_transcript(p, db, source_id=source_id)
    else:
        raise ValueError(f"Unsupported file format: '{ext}'. Supported: .pdf, .pptx, .txt")
