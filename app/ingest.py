from __future__ import annotations
import hashlib,re
from pathlib import Path
from .db import EvidenceDB
from .models import EvidenceUnit,Modality,SourceRecord
def _sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def _id(s,n):return f"{s}:e{n:05d}"
def ingest_pdf(path,db,source_id=None):
    import pymupdf
    p=Path(path); sid=source_id or _sha256(p)[:16]; doc=pymupdf.open(p)
    db.add_source(SourceRecord(source_id=sid,path=str(p),modality=Modality.pdf,title=p.stem,sha256=_sha256(p))); n=0
    for page_no,page in enumerate(doc,1):
        text=page.get_text("text").strip()
        for chunk in re.split(r"\n\s*\n",text):
            chunk=chunk.strip()
            if len(chunk)<20:continue
            n+=1; db.add_evidence(EvidenceUnit(evidence_id=_id(sid,n),source_id=sid,modality=Modality.pdf,text=chunk,location={"page":page_no}))
    return sid
def ingest_pptx(path,db,source_id=None):
    from pptx import Presentation
    p=Path(path); sid=source_id or _sha256(p)[:16]; prs=Presentation(p)
    db.add_source(SourceRecord(source_id=sid,path=str(p),modality=Modality.pptx,title=p.stem,sha256=_sha256(p))); n=0
    for slide_no,slide in enumerate(prs.slides,1):
        texts=[sh.text.strip() for sh in slide.shapes if hasattr(sh,"text_frame") and sh.text.strip()]
        if not texts:continue
        n+=1; db.add_evidence(EvidenceUnit(evidence_id=_id(sid,n),source_id=sid,modality=Modality.pptx,text="\n".join(texts),location={"slide":slide_no}))
    return sid
def ingest_transcript(path,db,source_id=None):
    p=Path(path); sid=source_id or _sha256(p)[:16]
    db.add_source(SourceRecord(source_id=sid,path=str(p),modality=Modality.video,title=p.stem,sha256=_sha256(p))); n=0
    for line in p.read_text(encoding="utf-8").splitlines():
        m=re.match(r"\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*(.*)",line.strip())
        if m:
            n+=1; db.add_evidence(EvidenceUnit(evidence_id=_id(sid,n),source_id=sid,modality=Modality.video,text=m.group(2),location={"timestamp":m.group(1)}))
    return sid
