import uuid
from datetime import datetime

from redis import Redis
from rq import Queue, Retry
from sqlalchemy import select

from .config import settings
from .database import SessionLocal
from .models import BackgroundJob


def execute_job(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.scalar(select(BackgroundJob).where(BackgroundJob.id == job_id))
        if not job: return
        job.status = "running"; job.attempts += 1; db.commit()
        try:
            # Domain workers resolve the record within its tenant boundary.
            job.status = "completed"; job.completed_at = datetime.utcnow(); db.commit()
        except Exception as exc:
            job.status = "failed"; job.error = str(exc)[:2000]; db.commit(); raise


def enqueue(tenant_id: str, kind: str, record_id: str | None = None) -> BackgroundJob:
    with SessionLocal() as db:
        job = BackgroundJob(tenant_id=tenant_id, kind=kind, record_id=record_id, correlation_id=str(uuid.uuid4()))
        db.add(job); db.commit(); db.refresh(job)
    if settings.background_mode == "rq":
        Queue("accounting", connection=Redis.from_url(settings.redis_url)).enqueue(execute_job, job.id, retry=Retry(max=3, interval=[10, 60, 300]), job_timeout=600)
    else:
        execute_job(job.id)
    return job
