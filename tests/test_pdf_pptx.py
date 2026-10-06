import base64,io
from app.db import EvidenceDB
from app.ingest import ingest_pdf, ingest_pptx
from app.source_resolver import resolve

PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")

def test_pdf_page_provenance(tmp_path):
    import pymupdf
    p=tmp_path/"sample.pdf"; d=pymupdf.open(); pg=d.new_page(); pg.insert_text((72,72),"Evidence on page one."); d.save(p)
    db=EvidenceDB(tmp_path/"db.sqlite"); ingest_pdf(p,db,"pdf1")
    rows=list(db.all_evidence()); assert rows and rows[0].location["page"]==1 and rows[0].source_id=="pdf1"

def test_pptx_slide_provenance(tmp_path):
    from pptx import Presentation
    prs=Presentation(); slide=prs.slides.add_slide(prs.slide_layouts[1]); slide.shapes.title.text="Evidence slide"; p=tmp_path/"sample.pptx"; prs.save(p)
    db=EvidenceDB(tmp_path/"db.sqlite"); ingest_pptx(p,db,"ppt1")
    rows=list(db.all_evidence()); assert rows and rows[0].location["slide"]==1 and rows[0].source_id=="ppt1"

def test_pdf_embedded_image_is_first_class_evidence(tmp_path):
    import pymupdf
    p=tmp_path/"image.pdf"; d=pymupdf.open(); pg=d.new_page(); pg.insert_text((72,72),"Figure context."); pg.insert_image(pymupdf.Rect(72,100,172,200),stream=PNG); d.save(p)
    db=EvidenceDB(tmp_path/"db.sqlite"); ingest_pdf(p,db,"pdfimg")
    images=[e for e in db.all_evidence() if e.evidence_type=="image"]
    assert len(images)==1
    e=images[0]
    assert e.modality.value=="image" and e.asset_id and e.location["page"]==1
    asset=db.get_asset(e.asset_id)
    assert asset and asset[2]=="image/png" and asset[6]==PNG

def test_pptx_embedded_image_is_first_class_evidence(tmp_path):
    from pptx import Presentation
    prs=Presentation(); slide=prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_picture(io.BytesIO(PNG),100,100)
    p=tmp_path/"image.pptx"; prs.save(p)
    db=EvidenceDB(tmp_path/"db.sqlite"); ingest_pptx(p,db,"pptimg")
    images=[e for e in db.all_evidence() if e.evidence_type=="image"]
    assert len(images)==1
    e=images[0]
    assert e.modality.value=="image" and e.asset_id and e.location["slide"]==1
    asset=db.get_asset(e.asset_id)
    assert asset and asset[2]=="image/png" and asset[6]==PNG

def test_image_source_resolution_preserves_provenance(tmp_path):
    import pymupdf
    p=tmp_path/"resolve.pdf"; d=pymupdf.open(); pg=d.new_page(); pg.insert_image(pymupdf.Rect(72,72,172,172),stream=PNG); d.save(p)
    db=EvidenceDB(tmp_path/"db.sqlite"); ingest_pdf(p,db,"resolve1")
    e=next(e for e in db.all_evidence() if e.evidence_type=="image")
    resolved=resolve(e.evidence_id,db)
    assert resolved["evidence_id"]==e.evidence_id
    assert resolved["source_id"]=="resolve1"
    assert resolved["location"]["page"]==1
    assert resolved["asset"]["asset_id"]==e.asset_id
    assert resolved["asset"]["mime_type"]=="image/png"
