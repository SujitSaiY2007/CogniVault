from app.db import EvidenceDB
from app.ingest import ingest_pdf, ingest_pptx
def test_pdf_page_provenance(tmp_path):
    import fitz
    p=tmp_path/"sample.pdf"; d=fitz.open(); pg=d.new_page(); pg.insert_text((72,72),"Evidence on page one."); d.save(p)
    db=EvidenceDB(tmp_path/"db.sqlite"); ingest_pdf(p,db,"pdf1")
    rows=list(db.all_evidence()); assert rows and rows[0].location["page"]==1 and rows[0].source_id=="pdf1"
def test_pptx_slide_provenance(tmp_path):
    from pptx import Presentation
    prs=Presentation(); slide=prs.slides.add_slide(prs.slide_layouts[1]); slide.shapes.title.text="Evidence slide"; p=tmp_path/"sample.pptx"; prs.save(p)
    db=EvidenceDB(tmp_path/"db.sqlite"); ingest_pptx(p,db,"ppt1")
    rows=list(db.all_evidence()); assert rows and rows[0].location["slide"]==1 and rows[0].source_id=="ppt1"
