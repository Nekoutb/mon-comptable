import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def uid() -> str:
    return str(uuid.uuid4())


class InvoiceStatus(str, enum.Enum):
    RECEIVED = "received"
    OCR_PENDING = "ocr_pending"
    REVIEW = "review"
    SUPPLIER_NOT_FOUND = "supplier_not_found"
    DUPLICATE = "duplicate"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ERP_DRAFT = "erp_draft"
    POSTED = "posted"
    FAILED = "failed"


class StatementStatus(str, enum.Enum):
    RECEIVED = "received"
    PARSED = "parsed"
    VALIDATED = "validated"
    IMPORTED = "imported"
    DUPLICATE = "duplicate"
    FAILED = "failed"


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LegalEntity(Base):
    __tablename__ = "legal_entities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    country: Mapped[str] = mapped_column(String(2), default="CM")
    framework: Mapped[str] = mapped_column(String(32), default="SYSCOHADA")
    currency: Mapped[str] = mapped_column(String(3), default="XAF")
    tax_id: Mapped[str | None] = mapped_column(String(80))


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="accountant")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    erp_id: Mapped[str] = mapped_column(String(80))
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(180), index=True)
    tax_id: Mapped[str | None] = mapped_column(String(80), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    bank_last4: Mapped[str | None] = mapped_column(String(4))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("tenant_id", "entity_id", "erp_id"),)


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    erp_id: Mapped[str] = mapped_column(String(80))
    code: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(180))
    type: Mapped[str] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    postable: Mapped[bool] = mapped_column(Boolean, default=True)


class TaxCode(Base):
    __tablename__ = "tax_codes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    rate: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    recoverable_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("100"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Journal(Base):
    __tablename__ = "journals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    erp_id: Mapped[str] = mapped_column(String(80))
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), default="XAF")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    media_type: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(30), default="upload")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    supplier_id: Mapped[str | None] = mapped_column(ForeignKey("suppliers.id"), index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(100), index=True)
    normalized_number: Mapped[str | None] = mapped_column(String(100), index=True)
    invoice_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="XAF")
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.RECEIVED, index=True)
    ocr_output: Mapped[dict | None] = mapped_column(JSON)
    ocr_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    duplicate_level: Mapped[str | None] = mapped_column(String(20))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (Index("ix_invoice_tenant_status_date", "tenant_id", "status", "invoice_date"),)


class AccountingProposal(Base):
    __tablename__ = "accounting_proposals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), unique=True)
    journal_id: Mapped[str] = mapped_column(ForeignKey("journals.id"))
    debit_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    credit_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    tax_code_id: Mapped[str | None] = mapped_column(ForeignKey("tax_codes.id"))
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    explanation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    model_version: Mapped[str] = mapped_column(String(80), default="deterministic-mock-v1")
    prompt_version: Mapped[str] = mapped_column(String(40), default="ap-v1")
    validated: Mapped[bool] = mapped_column(Boolean, default=False)


class ApprovalAction(Base):
    __tablename__ = "approval_actions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(30))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ERPPosting(Base):
    __tablename__ = "erp_postings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    record_type: Mapped[str] = mapped_column(String(30))
    record_id: Mapped[str] = mapped_column(String(36), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    mode: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    external_reference: Mapped[str | None] = mapped_column(String(120))
    response: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BankStatement(Base):
    __tablename__ = "bank_statements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    journal_id: Mapped[str | None] = mapped_column(ForeignKey("journals.id"))
    reference: Mapped[str] = mapped_column(String(120), index=True)
    format: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), default="XAF")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    status: Mapped[StatementStatus] = mapped_column(Enum(StatementStatus), default=StatementStatus.RECEIVED)
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("tenant_id", "checksum"),)


class BankStatementLine(Base):
    __tablename__ = "bank_statement_lines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    statement_id: Mapped[str] = mapped_column(ForeignKey("bank_statements.id"), index=True)
    transaction_date: Mapped[date] = mapped_column(Date)
    value_date: Mapped[date | None] = mapped_column(Date)
    reference: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    line_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), default="unallocated")
    error: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    record_type: Mapped[str] = mapped_column(String(50))
    record_id: Mapped[str] = mapped_column(String(36), index=True)
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    origin: Mapped[str] = mapped_column(String(20), default="human")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class InboundEmail(Base):
    __tablename__ = "inbound_emails"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    message_id: Mapped[str] = mapped_column(String(255))
    sender: Mapped[str] = mapped_column(String(255))
    recipient: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="received", index=True)
    attachment_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("tenant_id", "message_id"),)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    record_type: Mapped[str | None] = mapped_column(String(50))
    record_id: Mapped[str | None] = mapped_column(String(36))
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    kind: Mapped[str] = mapped_column(String(60), index=True)
    record_id: Mapped[str | None] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
