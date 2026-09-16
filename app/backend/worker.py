import time
from threading import Event, Thread
from tempfile import TemporaryDirectory
from pathlib import Path

from sqlalchemy import and_, or_, select, update

from .db import DATA, Document, Fact, Job, Session, User, audit, uid
from .providers import ServiceError, extract_facts, infer_report_date, parse_pages
from .retrieval import sync_fact_chunk
from .storage import get

def process_one(document_id=None):
    now=time.time(); claim=uid()
    with Session() as db:
        condition=or_(Job.state=="queued",and_(Job.state=="running",Job.lease<now))
        if document_id: condition=and_(condition,Job.document_id==document_id)
        job=db.scalar(select(Job).where(condition).limit(1))
        if not job: return False
        result=db.execute(update(Job).where(Job.id==job.id,Job.state==job.state,Job.lease==job.lease).values(state="running",lease=now+600,claim=claim,attempts=Job.attempts+1))
        if result.rowcount!=1: db.rollback(); return True
        doc=db.get(Document,job.document_id)
        doc.status="processing"; doc.error=""
        user=db.get(User,doc.user_id)
        doc_id,user_id,ext,is_demo=doc.id,doc.user_id,doc.extension,user.demo
        db.commit()
    try:
        content=get(user_id,doc_id,ext)
        with TemporaryDirectory(prefix="apex-document-") as folder:
            path=Path(folder)/("document"+ext)
            path.write_bytes(content)
            pages=parse_pages(path,ext)
        items,method=extract_facts(pages,demo=is_demo)
        with Session() as db:
            job=db.scalar(select(Job).where(Job.document_id==doc_id,Job.claim==claim,Job.state=="running"))
            doc=db.get(Document,doc_id)
            if not job or not doc: return True  # Deleted/cancelled while processing.
            existing=db.scalars(select(Fact).where(Fact.user_id==user_id)).all()
            for data in items:
                conflict=any(f.category==data["category"] and f.value!=data["value"] and f.scheduled_date and data["scheduled_date"] and f.scheduled_date!=data["scheduled_date"] for f in existing)
                fact=Fact(user_id=user_id,document_id=doc_id,**data,status="pending",conflict=conflict)
                db.add(fact); db.flush(); sync_fact_chunk(db,fact,doc)
            doc.pages=pages; doc.report_date=infer_report_date(pages); doc.method=method; doc.status="ready"; job.state="done"; job.lease=0
            audit(db,user_id,"document_processed",doc_id,{"fact_count":len(items)})
            db.commit()
    except Exception as exc:
        with Session() as db:
            job=db.scalar(select(Job).where(Job.document_id==doc_id,Job.claim==claim,Job.state=="running"))
            doc=db.get(Document,doc_id)
            if job and doc:
                job.state="failed"; job.lease=0; doc.status="failed"
                doc.error=str(exc) if isinstance(exc,ServiceError) else "处理暂未完成，资料已保留，请重试。"
                db.commit()
    return True

class Worker:
    def __init__(self): self.stop=Event(); self.thread=None
    def start(self):
        self.thread=Thread(target=self.run,daemon=True,name="apex-document-worker"); self.thread.start()
    def run(self):
        while not self.stop.is_set():
            try: process_one()
            except Exception: pass  # No raw document/provider output enters logs.
            self.stop.wait(1)
    def close(self):
        self.stop.set()
        if self.thread: self.thread.join(timeout=2)
