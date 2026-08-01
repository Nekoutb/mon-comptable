import hashlib
import os
import uuid
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .adapters import erp_adapter, ocr_adapter
from .config import settings
from .database import Base, engine, get_db
from .models import AccountingProposal, ApprovalAction, AuditLog, BackgroundJob, BankStatement, BankStatementLine, Document, InboundEmail, Invoice, InvoiceStatus, Journal, LegalEntity, Notification, StatementStatus, Supplier, Tenant, User
from .schemas import ApprovalInput, InvoiceOut, InvoiceUpdate, LoginRequest, RejectInput, StatementOut, TokenResponse
from .security import create_token, current_user, roles, verify_password
from .services import audit, duplicate_check, generate_proposal, match_supplier, normalize_invoice_number, parse_bank_content, post_invoice

@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.assert_secure()
    Base.metadata.create_all(engine)
    os.makedirs(settings.storage_root, exist_ok=True)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", openapi_url="/api/v1/openapi.json", docs_url="/api/docs", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def correlation(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": f"HTTP_{exc.status_code}", "message": exc.detail}})


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version, "erp": erp_adapter.health_check(), "ocr": {"provider": "mock", "external_connection": False}}


@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower(), User.active.is_(True)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return TokenResponse(access_token=create_token(user))


@app.get("/api/v1/users/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "tenant_id": user.tenant_id, "email": user.email, "name": user.name, "role": user.role}


@app.get("/api/v1/master-data/{kind}")
def master_data(kind: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    mapping = {"suppliers": Supplier, "journals": Journal}
    model = mapping.get(kind)
    if not model: raise HTTPException(404, "Unsupported master-data type")
    return db.scalars(select(model).where(model.tenant_id == user.tenant_id)).all()


def entity_for(db: Session, user: User, entity_id: str | None) -> LegalEntity:
    query = select(LegalEntity).where(LegalEntity.tenant_id == user.tenant_id)
    if entity_id: query = query.where(LegalEntity.id == entity_id)
    entity = db.scalar(query)
    if not entity: raise HTTPException(404, "Legal entity not found")
    return entity


async def save_upload(file: UploadFile, entity: LegalEntity, user: User, db: Session) -> tuple[Document, bytes]:
    allowed = {"application/pdf", "image/jpeg", "image/png", "image/tiff", "text/csv", "application/vnd.ms-excel", "text/plain"}
    if file.content_type not in allowed: raise HTTPException(415, "Unsupported or unsafe file type")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, "File too large")
    digest = hashlib.sha256(content).hexdigest()
    key = f"{user.tenant_id}/{entity.id}/{date.today().isoformat()}/{uuid.uuid4()}-{os.path.basename(file.filename or 'document')}"
    path = os.path.join(settings.storage_root, key.replace("/", os.sep)); os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as stream: stream.write(content)
    doc = Document(tenant_id=user.tenant_id, entity_id=entity.id, filename=os.path.basename(file.filename or "document"), storage_key=key, media_type=file.content_type or "application/octet-stream", sha256=digest, size=len(content))
    db.add(doc); db.flush()
    return doc, content


@app.post("/api/v1/invoices/upload", response_model=InvoiceOut)
async def upload_invoice(file: UploadFile = File(...), entity_id: str | None = None, user: User = Depends(roles("accountant", "tenant_admin")), db: Session = Depends(get_db)):
    entity = entity_for(db, user, entity_id); doc, content = await save_upload(file, entity, user, db)
    duplicate_doc = db.scalar(select(Document).where(Document.tenant_id == user.tenant_id, Document.sha256 == doc.sha256, Document.id != doc.id))
    invoice = Invoice(tenant_id=user.tenant_id, entity_id=entity.id, document_id=doc.id, status=InvoiceStatus.DUPLICATE if duplicate_doc else InvoiceStatus.OCR_PENDING, duplicate_level="exact" if duplicate_doc else None, created_by=user.id)
    db.add(invoice); db.flush(); audit(db, user, "invoice_uploaded", "invoice", invoice.id, after={"filename": doc.filename, "sha256": doc.sha256})
    if not duplicate_doc:
        output = ocr_adapter.extract(doc.filename, content); invoice.ocr_output = {k: str(v) if isinstance(v, Decimal) else v for k, v in output.items()}; invoice.ocr_confidence = output["confidence"]
        invoice.invoice_number = output["invoice_number"]; invoice.normalized_number = normalize_invoice_number(invoice.invoice_number); invoice.invoice_date = date.fromisoformat(output["invoice_date"]); invoice.currency = output["currency"]; invoice.net_amount = Decimal(output["net_amount"]); invoice.tax_amount = Decimal(output["tax_amount"]); invoice.gross_amount = Decimal(output["gross_amount"]); invoice.description = output["description"]; invoice.status = InvoiceStatus.REVIEW
        audit(db, user, "ocr_completed", "invoice", invoice.id, after={"provider": "mock", "confidence": str(invoice.ocr_confidence)}, origin="automation")
    db.commit(); db.refresh(invoice); return invoice


@app.get("/api/v1/invoices", response_model=list[InvoiceOut])
def list_invoices(status: InvoiceStatus | None = None, limit: int = 50, offset: int = 0, user: User = Depends(current_user), db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    query = select(Invoice).where(Invoice.tenant_id == user.tenant_id)
    if status: query = query.where(Invoice.status == status)
    return db.scalars(query.order_by(Invoice.created_at.desc()).limit(limit).offset(offset)).all()


@app.patch("/api/v1/invoices/{invoice_id}", response_model=InvoiceOut)
def update_invoice(invoice_id: str, payload: InvoiceUpdate, user: User = Depends(roles("accountant", "tenant_admin")), db: Session = Depends(get_db)):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id))
    if not invoice: raise HTTPException(404, "Invoice not found")
    before = {k: str(getattr(invoice, k)) for k in payload.model_fields_set}
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(invoice, key, value)
    invoice.normalized_number = normalize_invoice_number(invoice.invoice_number); invoice.version += 1
    audit(db, user, "invoice_corrected", "invoice", invoice.id, before=before, after=payload.model_dump(mode="json", exclude_unset=True)); db.commit(); db.refresh(invoice); return invoice


@app.post("/api/v1/invoices/{invoice_id}/match-supplier")
def invoice_match(invoice_id: str, user: User = Depends(roles("accountant", "tenant_admin")), db: Session = Depends(get_db)):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id))
    if not invoice: raise HTTPException(404, "Invoice not found")
    result = match_supplier(db, invoice, user); db.commit(); return result


@app.post("/api/v1/invoices/{invoice_id}/check-duplicate")
def invoice_duplicate(invoice_id: str, user: User = Depends(roles("accountant", "tenant_admin")), db: Session = Depends(get_db)):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id))
    if not invoice: raise HTTPException(404, "Invoice not found")
    result = duplicate_check(db, invoice, user); db.commit(); return result


@app.post("/api/v1/invoices/{invoice_id}/generate-proposal")
def proposal(invoice_id: str, user: User = Depends(roles("accountant", "tenant_admin")), db: Session = Depends(get_db)):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id))
    if not invoice: raise HTTPException(404, "Invoice not found")
    result = generate_proposal(db, invoice, user); db.commit(); return {"id": result.id, "debit": result.debit, "credit": result.credit, "confidence": result.confidence, "explanation": result.explanation, "validated": result.validated}


@app.post("/api/v1/invoices/{invoice_id}/submit")
def submit_invoice(invoice_id: str, user: User = Depends(roles("accountant")), db: Session = Depends(get_db)):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id))
    proposal = db.scalar(select(AccountingProposal).where(AccountingProposal.invoice_id == invoice_id, AccountingProposal.tenant_id == user.tenant_id))
    if not invoice or not proposal or not proposal.validated: raise HTTPException(409, "Validated proposal required")
    invoice.status = InvoiceStatus.PENDING_APPROVAL; audit(db, user, "submitted_for_approval", "invoice", invoice.id); db.commit(); return {"status": invoice.status}


@app.post("/api/v1/invoices/{invoice_id}/approve")
def approve(invoice_id: str, payload: ApprovalInput, user: User = Depends(roles("approver", "tenant_admin")), db: Session = Depends(get_db)):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id))
    if not invoice or invoice.status != InvoiceStatus.PENDING_APPROVAL: raise HTTPException(409, "Invoice is not pending approval")
    if invoice.created_by == user.id: raise HTTPException(409, "Four-eyes control prevents self-approval")
    invoice.status = InvoiceStatus.APPROVED; db.add(ApprovalAction(tenant_id=user.tenant_id, invoice_id=invoice.id, user_id=user.id, action="approved", comment=payload.comment)); audit(db, user, "approved", "invoice", invoice.id, reason=payload.comment); db.commit(); return {"status": invoice.status}


@app.post("/api/v1/invoices/{invoice_id}/reject")
def reject(invoice_id: str, payload: RejectInput, user: User = Depends(roles("approver", "tenant_admin")), db: Session = Depends(get_db)):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id))
    if not invoice: raise HTTPException(404, "Invoice not found")
    invoice.status = InvoiceStatus.REVIEW; db.add(ApprovalAction(tenant_id=user.tenant_id, invoice_id=invoice.id, user_id=user.id, action="rejected", comment=payload.comment)); audit(db, user, "rejected", "invoice", invoice.id, reason=payload.comment); db.commit(); return {"status": invoice.status}


@app.post("/api/v1/invoices/{invoice_id}/{operation}")
def erp_invoice(invoice_id: str, operation: str, idempotency_key: str = Header(..., alias="Idempotency-Key"), user: User = Depends(roles("poster", "tenant_admin")), db: Session = Depends(get_db)):
    if operation != "record-draft": raise HTTPException(403, "Direct ERP posting is disabled; create a draft for manual posting")
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id))
    if not invoice: raise HTTPException(404, "Invoice not found")
    result = post_invoice(db, invoice, user, idempotency_key, "draft"); db.commit(); return {"status": result.status, "external_reference": result.external_reference, "posting_required": True, "mocked": True}


@app.get("/api/v1/invoices/{invoice_id}/audit-log")
def invoice_audit(invoice_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(AuditLog).where(AuditLog.tenant_id == user.tenant_id, AuditLog.record_type == "invoice", AuditLog.record_id == invoice_id).order_by(AuditLog.created_at)).all()


@app.post("/api/v1/bank-statements/upload", response_model=StatementOut)
async def upload_statement(file: UploadFile = File(...), entity_id: str | None = None, journal_id: str | None = None, opening_balance: Decimal = 0, closing_balance: Decimal = 0, user: User = Depends(roles("accountant", "tenant_admin")), db: Session = Depends(get_db)):
    entity = entity_for(db, user, entity_id); doc, content = await save_upload(file, entity, user, db)
    existing = db.scalar(select(BankStatement).where(BankStatement.tenant_id == user.tenant_id, BankStatement.checksum == doc.sha256))
    if existing: raise HTTPException(409, "Duplicate bank statement")
    if journal_id and not db.scalar(select(Journal).where(Journal.id == journal_id, Journal.tenant_id == user.tenant_id, Journal.entity_id == entity.id, Journal.kind == "bank")): raise HTTPException(422, "Invalid bank journal")
    extension = os.path.splitext(doc.filename)[1].lower()
    fmt = "camt053" if extension in {".xml", ".camt"} else "mt940" if extension in {".mt940", ".sta"} else "csv"
    statement = BankStatement(tenant_id=user.tenant_id, entity_id=entity.id, document_id=doc.id, journal_id=journal_id, reference=os.path.splitext(doc.filename)[0], format=fmt, opening_balance=opening_balance, closing_balance=closing_balance, checksum=doc.sha256, created_by=user.id)
    db.add(statement); db.flush(); parse_bank_content(db, statement, content, user); db.commit(); db.refresh(statement); return statement


@app.get("/api/v1/bank-statements", response_model=list[StatementOut])
def statements(limit: int = 50, offset: int = 0, user: User = Depends(current_user), db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    return db.scalars(select(BankStatement).where(BankStatement.tenant_id == user.tenant_id).order_by(BankStatement.created_at.desc()).limit(limit).offset(offset)).all()


@app.post("/api/v1/bank-statements/{statement_id}/validate")
def validate_statement(statement_id: str, user: User = Depends(roles("accountant", "tenant_admin")), db: Session = Depends(get_db)):
    statement = db.scalar(select(BankStatement).where(BankStatement.id == statement_id, BankStatement.tenant_id == user.tenant_id))
    if not statement or not statement.journal_id: raise HTTPException(409, "Bank journal must be selected")
    line_total = db.scalar(select(func.coalesce(func.sum(BankStatementLine.amount), 0)).where(BankStatementLine.statement_id == statement.id, BankStatementLine.tenant_id == user.tenant_id))
    expected = statement.opening_balance + line_total
    if expected != statement.closing_balance: raise HTTPException(422, f"Statement does not balance; expected closing balance {expected}")
    statement.status = StatementStatus.VALIDATED; audit(db, user, "bank_statement_validated", "bank_statement", statement.id, after={"line_total": str(line_total)}); db.commit(); return {"status": statement.status, "line_total": line_total}


@app.post("/api/v1/bank-statements/{statement_id}/record-draft")
def draft_statement(statement_id: str, idempotency_key: str = Header(..., alias="Idempotency-Key"), user: User = Depends(roles("poster", "tenant_admin")), db: Session = Depends(get_db)):
    statement = db.scalar(select(BankStatement).where(BankStatement.id == statement_id, BankStatement.tenant_id == user.tenant_id))
    if not statement or statement.status != StatementStatus.VALIDATED: raise HTTPException(409, "Validated statement required")
    response = erp_adapter.post_bank_statement({"statement_id": statement.id, "posting_status": "draft"}, idempotency_key); statement.status = StatementStatus.IMPORTED; audit(db, user, "bank_statement_draft_created", "bank_statement", statement.id, after=response, origin="automation"); db.commit(); return {**response, "posting_required": True}


@app.get("/api/v1/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    invoice_counts = dict(db.execute(select(Invoice.status, func.count()).where(Invoice.tenant_id == user.tenant_id).group_by(Invoice.status)).all())
    statement_counts = dict(db.execute(select(BankStatement.status, func.count()).where(BankStatement.tenant_id == user.tenant_id).group_by(BankStatement.status)).all())
    return {"accounts_payable": {str(k.value): v for k, v in invoice_counts.items()}, "treasury": {str(k.value): v for k, v in statement_counts.items()}, "integrations": {"erp": erp_adapter.health_check(), "ocr": {"provider": "mock", "external_connection": False}}}


@app.post("/api/v1/inbound-email/webhook")
def inbound_email(payload: dict, x_webhook_secret: str = Header(..., alias="X-Webhook-Secret"), db: Session = Depends(get_db)):
    if not __import__("secrets").compare_digest(x_webhook_secret, settings.inbound_webhook_secret):
        raise HTTPException(401, "Invalid webhook signature")
    recipient = str(payload.get("recipient", "")); message_id = str(payload.get("message_id", ""))
    if not recipient or not message_id: raise HTTPException(422, "recipient and message_id are required")
    local = recipient.split("@", 1)[0]; tenant_code = local.split("+", 1)[1] if "+" in local else ""
    tenant = db.scalar(select(Tenant).where(Tenant.code == tenant_code, Tenant.active.is_(True)))
    if not tenant: raise HTTPException(404, "Inbound tenant address not recognized")
    existing = db.scalar(select(InboundEmail).where(InboundEmail.tenant_id == tenant.id, InboundEmail.message_id == message_id))
    if existing: return {"id": existing.id, "status": existing.status, "duplicate_delivery": True}
    attachments = payload.get("attachments", [])
    unsafe = [a for a in attachments if str(a.get("filename", "")).lower().endswith((".exe", ".js", ".bat", ".cmd", ".ps1"))]
    email = InboundEmail(tenant_id=tenant.id, message_id=message_id, sender=str(payload.get("sender", "")), recipient=recipient, subject=str(payload.get("subject", ""))[:500], attachment_count=len(attachments), status="quarantined" if unsafe else "received", error="Unsafe attachment type" if unsafe else None)
    db.add(email); db.flush(); db.add(Notification(tenant_id=tenant.id, kind="invoice_email_received", title="New invoice email", message=f"Invoice email received from {email.sender}", record_type="inbound_email", record_id=email.id)); db.commit(); return {"id": email.id, "status": email.status, "mocked_provider": True}


@app.get("/api/v1/inbound-email/exceptions")
def email_exceptions(user: User = Depends(roles("accountant", "tenant_admin")), db: Session = Depends(get_db)):
    return db.scalars(select(InboundEmail).where(InboundEmail.tenant_id == user.tenant_id, InboundEmail.status.in_(["quarantined", "failed", "unmatched"]))).all()


@app.get("/api/v1/notifications")
def notifications(limit: int = 50, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Notification).where(Notification.tenant_id == user.tenant_id).order_by(Notification.created_at.desc()).limit(min(max(limit, 1), 100))).all()


@app.get("/api/v1/admin/jobs")
def jobs(limit: int = 50, user: User = Depends(roles("tenant_admin")), db: Session = Depends(get_db)):
    return db.scalars(select(BackgroundJob).where(BackgroundJob.tenant_id == user.tenant_id).order_by(BackgroundJob.created_at.desc()).limit(min(max(limit, 1), 100))).all()
