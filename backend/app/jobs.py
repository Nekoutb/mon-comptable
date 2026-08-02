import os
import uuid
from datetime import date, datetime
from decimal import Decimal

from redis import Redis
from rq import Queue, Retry
from sqlalchemy import select
from sqlalchemy.orm import Session

from .adapters import ocr_adapter
from .config import settings
from .context import correlation_id_var
from .database import SessionLocal
from .models import BackgroundJob, Document, Invoice, InvoiceStatus
from .services import audit, normalize_invoice_number


def handle_invoice_ocr(db: Session, job: BackgroundJob) -> None:
    invoice = db.scalar(select(Invoice).where(Invoice.id == job.record_id, Invoice.tenant_id == job.tenant_id))
    if not invoice or invoice.status != InvoiceStatus.OCR_PENDING:
        return
    document = db.scalar(select(Document).where(Document.id == invoice.document_id, Document.tenant_id == job.tenant_id))
    if not document:
        raise ValueError("Invoice document is missing")
    path = os.path.join(settings.storage_root, document.storage_key.replace("/", os.sep))
    with open(path, "rb") as stream:
        content = stream.read()
    output = ocr_adapter.extract(document.filename, content)
    invoice.ocr_output = {k: str(v) if isinstance(v, Decimal) else v for k, v in output.items()}
    invoice.ocr_confidence = output["confidence"]
    invoice.invoice_number = output["invoice_number"]
    invoice.normalized_number = normalize_invoice_number(invoice.invoice_number)
    invoice.invoice_date = date.fromisoformat(output["invoice_date"])
    invoice.currency = output["currency"]
    invoice.net_amount = Decimal(output["net_amount"])
    invoice.tax_amount = Decimal(output["tax_amount"])
    invoice.gross_amount = Decimal(output["gross_amount"])
    invoice.description = output["description"]
    invoice.status = InvoiceStatus.REVIEW
    audit(db, None, "ocr_completed", "invoice", invoice.id, after={"provider": "mock", "confidence": str(invoice.ocr_confidence)}, origin="automation", tenant_id=job.tenant_id)


HANDLERS = {"invoice_ocr": handle_invoice_ocr}


def execute_job(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.scalar(select(BackgroundJob).where(BackgroundJob.id == job_id))
        if not job or job.status == "completed":
            return
        job.status = "running"; job.attempts += 1; db.commit()
        handler = HANDLERS.get(job.kind)
        try:
            if not handler:
                raise ValueError(f"No handler registered for job kind {job.kind}")
            handler(db, job)
            job.status = "completed"; job.completed_at = datetime.utcnow(); db.commit()
        except Exception as exc:
            db.rollback()
            job.status = "failed" if job.attempts >= job.max_attempts else "queued"
            job.error = str(exc)[:2000]; db.commit(); raise


def enqueue(tenant_id: str, kind: str, record_id: str | None = None) -> BackgroundJob:
    with SessionLocal() as db:
        job = BackgroundJob(tenant_id=tenant_id, kind=kind, record_id=record_id, correlation_id=correlation_id_var.get() or str(uuid.uuid4()))
        db.add(job); db.commit(); db.refresh(job)
    if settings.background_mode == "rq":
        Queue("accounting", connection=Redis.from_url(settings.redis_url)).enqueue(execute_job, job.id, retry=Retry(max=3, interval=[10, 60, 300]), job_timeout=600)
    else:
        execute_job(job.id)
    return job
