from __future__ import annotations
import hashlib,re
from pathlib import Path
from .db import EvidenceDB
from .models import EvidenceUnit,Modality,SourceRecord

def _sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def _bytes_sha256(data): return hashlib.sha256(data).hexdigest()
def _id(s,n): return f"{s}:e{n:05d}"
def _asset_id(data): return "asset:"+_bytes_sha256(data)[:24]

def _mime_from_ext(ext):
    return {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","gif":"image/gif","bmp":"image/bmp","webp":"image/webp","tiff":"image/tiff","tif":"image/tiff"}.get(ext.lower().lstrip("."),"application/octet-stream")

def _add_image_evidence(db,sid,eid,modality,location,data,mime_type,width=None,height=None):
    digest=_bytes_sha256(data); aid=_asset_id(data)
    db.add_evidence(EvidenceUnit(evidence_id=eid,source_id=sid,modality=Modality.image,text="Embedded figure/image evidence",location=location,evidence_type="image",asset_id=aid,metadata={"mime_type":mime_type,"sha256":digest}))
    db.add_asset(aid,eid,mime_type,digest,data,width,height)

def ingest_pdf(path,db,source_id=None):
    import pymupdf
    p=Path(path); sid=source_id or _sha256(p)[:16]; doc=pymupdf.open(p)
    db.add_source(SourceRecord(source_id=sid,path=str(p),modality=Modality.pdf,title=p.stem,sha256=_sha256(p))); n=0
    for page_no,page in enumerate(doc,1):
        text=page.get_text("text").strip()
        for chunk in re.split(r"\n\s*\n",text):
            chunk=chunk.strip()
            if len(chunk)<20: continue
            n+=1; db.add_evidence(EvidenceUnit(evidence_id=_id(sid,n),source_id=sid,modality=Modality.pdf,text=chunk,location={"page":page_no}))
        for img in page.get_images(full=True):
            xref=img[0]; extracted=doc.extract_image(xref); data=extracted["image"]; n+=1
            _add_image_evidence(db,sid,_id(sid,n),Modality.pdf,{"page":page_no,"image_xref":xref},data,_mime_from_ext(extracted["ext"]),extracted.get("width"),extracted.get("height"))
    return sid

def ingest_pptx(path,db,source_id=None):
    from pptx import Presentation
    p=Path(path); sid=source_id or _sha256(p)[:16]; prs=Presentation(p)
    db.add_source(SourceRecord(source_id=sid,path=str(p),modality=Modality.pptx,title=p.stem,sha256=_sha256(p))); n=0
    for slide_no,slide in enumerate(prs.slides,1):
        texts=[sh.text.strip() for sh in slide.shapes if hasattr(sh,"text_frame") and sh.text.strip()]
        if texts:
            n+=1; db.add_evidence(EvidenceUnit(evidence_id=_id(sid,n),source_id=sid,modality=Modality.pptx,text="\n".join(texts),location={"slide":slide_no}))
        for shape in slide.shapes:
            if shape.shape_type == 13:
                image=shape.image; data=image.blob; n+=1
                _add_image_evidence(db,sid,_id(sid,n),Modality.pptx,{"slide":slide_no,"shape_id":shape.shape_id},data,image.content_type,shape.width,shape.height)
    return sid

def ingest_transcript(path,db,source_id=None):
    p=Path(path); sid=source_id or _sha256(p)[:16]
    db.add_source(SourceRecord(source_id=sid,path=str(p),modality=Modality.video,title=p.stem,sha256=_sha256(p))); n=0
    for line in p.read_text(encoding="utf-8").splitlines():
        m=re.match(r"\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*(.*)",line.strip())
        if m:
            n+=1; db.add_evidence(EvidenceUnit(evidence_id=_id(sid,n),source_id=sid,modality=Modality.video,text=m.group(2),location={"timestamp":m.group(1)}))
    return sid
