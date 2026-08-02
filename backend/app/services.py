import hashlib
import re
import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .adapters import erp_adapter
from .context import correlation_id_var
from .models import Account, AccountingProposal, AuditLog, BankStatement, BankStatementLine, ERPPosting, Invoice, InvoiceStatus, Journal, StatementStatus, Supplier, TaxCode, User
from .parsers import parse_statement

# Statuses in which an invoice is frozen for edits and automated re-processing.
LOCKED_STATUSES = {InvoiceStatus.PENDING_APPROVAL, InvoiceStatus.APPROVED, InvoiceStatus.ERP_DRAFT, InvoiceStatus.POSTED}


def audit(db: Session, user: User | None, action: str, record_type: str, record_id: str, before=None, after=None, reason=None, origin="human", tenant_id: str | None = None):
    db.add(AuditLog(tenant_id=tenant_id or user.tenant_id, user_id=user.id if user else None, action=action, record_type=record_type, record_id=record_id, before=before, after=after, reason=reason, correlation_id=correlation_id_var.get() or str(uuid.uuid4()), origin=origin))


def ensure_unlocked(invoice: Invoice) -> None:
    if invoice.status in LOCKED_STATUSES:
        raise HTTPException(409, f"Invoice is locked in status {invoice.status.value}")


def normalize_invoice_number(value: str | None) -> str | None:
    return re.sub(r"[^A-Z0-9]", "", value.upper()) if value else None


def match_supplier(db: Session, invoice: Invoice, user: User) -> dict:
    ensure_unlocked(invoice)
    extracted = invoice.ocr_output or {}
    suppliers = db.scalars(select(Supplier).where(Supplier.tenant_id == user.tenant_id, Supplier.entity_id == invoice.entity_id, Supplier.active.is_(True))).all()
    candidates = []
    for supplier in suppliers:
        score, matches, conflicts = 0, [], []
        if extracted.get("supplier_tax_id") and supplier.tax_id == extracted["supplier_tax_id"]:
            score += 70; matches.append("tax_id")
        if extracted.get("supplier_name") and supplier.name.casefold() == extracted["supplier_name"].casefold():
            score += 25; matches.append("legal_name")
        if supplier.blocked:
            score = 0; conflicts.append("supplier_blocked")
        candidates.append({"supplier_id": supplier.id, "name": supplier.name, "confidence": score, "matches": matches, "conflicts": conflicts})
    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    best = candidates[0] if candidates else None
    if best and best["confidence"] >= 80:
        invoice.supplier_id = best["supplier_id"]
        invoice.status = InvoiceStatus.REVIEW
    else:
        invoice.status = InvoiceStatus.SUPPLIER_NOT_FOUND
    audit(db, user, "supplier_match", "invoice", invoice.id, after=best, origin="automation")
    return {"recommended": best, "alternatives": candidates[1:4]}


def duplicate_check(db: Session, invoice: Invoice, user: User) -> dict:
    ensure_unlocked(invoice)
    base = select(Invoice).where(Invoice.tenant_id == user.tenant_id, Invoice.entity_id == invoice.entity_id, Invoice.id != invoice.id, Invoice.supplier_id == invoice.supplier_id)
    exact = db.scalar(base.where(Invoice.normalized_number == invoice.normalized_number, Invoice.gross_amount == invoice.gross_amount)) if invoice.supplier_id else None
    probable = None
    if not exact and invoice.supplier_id and invoice.normalized_number:
        probable = db.scalar(base.where(Invoice.normalized_number == invoice.normalized_number, Invoice.gross_amount != invoice.gross_amount))
    matched = exact or probable
    level = "exact" if exact else "probable" if probable else "none"
    invoice.duplicate_level = level
    if exact:
        invoice.status = InvoiceStatus.DUPLICATE
    elif invoice.status == InvoiceStatus.DUPLICATE:
        invoice.status = InvoiceStatus.REVIEW
    audit(db, user, "duplicate_check", "invoice", invoice.id, after={"level": level, "matched_invoice_id": matched.id if matched else None}, origin="automation")
    return {"level": level, "matched_invoice_id": matched.id if matched else None, "posting_blocked": level in {"exact", "probable"}}


def generate_proposal(db: Session, invoice: Invoice, user: User) -> AccountingProposal:
    ensure_unlocked(invoice)
    if not invoice.supplier_id:
        raise HTTPException(409, "Supplier must be matched first")
    if invoice.duplicate_level in {"exact", "probable"}:
        raise HTTPException(409, "Unresolved duplicate blocks proposal")
    debit = db.scalar(select(Account).where(Account.tenant_id == user.tenant_id, Account.entity_id == invoice.entity_id, Account.type == "expense", Account.active.is_(True), Account.postable.is_(True)))
    credit = db.scalar(select(Account).where(Account.tenant_id == user.tenant_id, Account.entity_id == invoice.entity_id, Account.type == "payable", Account.active.is_(True), Account.postable.is_(True)))
    journal = db.scalar(select(Journal).where(Journal.tenant_id == user.tenant_id, Journal.entity_id == invoice.entity_id, Journal.kind == "purchase", Journal.active.is_(True)))
    tax = db.scalar(select(TaxCode).where(TaxCode.tenant_id == user.tenant_id, TaxCode.entity_id == invoice.entity_id, TaxCode.active.is_(True)))
    if not all((debit, credit, journal)):
        raise HTTPException(409, "ERP-synchronized account and journal master data is incomplete")
    proposal = db.scalar(select(AccountingProposal).where(AccountingProposal.invoice_id == invoice.id))
    values = dict(tenant_id=user.tenant_id, invoice_id=invoice.id, journal_id=journal.id, debit_account_id=debit.id, credit_account_id=credit.id, tax_code_id=tax.id if tax else None, debit=invoice.gross_amount, credit=invoice.gross_amount, explanation=f"Account {debit.code} is active in ERP master data and matches the expense category. Supplier payable account {credit.code} balances the proposal.", confidence=Decimal("91.00"), validated=True)
    if proposal:
        for key, value in values.items(): setattr(proposal, key, value)
    else:
        proposal = AccountingProposal(**values); db.add(proposal)
    invoice.status = InvoiceStatus.REVIEW
    audit(db, user, "proposal_generated", "invoice", invoice.id, after={"debit": str(invoice.gross_amount), "credit": str(invoice.gross_amount)}, origin="automation")
    return proposal


def claim_idempotency(db: Session, user: User, key: str, record_type: str, record_id: str, mode: str) -> ERPPosting | None:
    existing = db.scalar(select(ERPPosting).where(ERPPosting.idempotency_key == key, ERPPosting.tenant_id == user.tenant_id))
    if not existing:
        return None
    if existing.record_type != record_type or existing.record_id != record_id or existing.mode != mode:
        raise HTTPException(409, "Idempotency key already used for a different operation")
    return existing


def post_invoice(db: Session, invoice: Invoice, user: User, key: str, mode: str) -> ERPPosting:
    existing = claim_idempotency(db, user, key, "invoice", invoice.id, mode)
    if existing:
        return existing
    if invoice.status not in {InvoiceStatus.APPROVED, InvoiceStatus.ERP_DRAFT}:
        raise HTTPException(409, "Invoice must be approved before ERP recording")
    proposal = db.scalar(select(AccountingProposal).where(AccountingProposal.invoice_id == invoice.id, AccountingProposal.tenant_id == user.tenant_id))
    if not proposal or not proposal.validated or proposal.debit != proposal.credit:
        raise HTTPException(409, "A balanced validated proposal is required")
    if proposal.debit != invoice.gross_amount:
        raise HTTPException(409, "Proposal is stale; regenerate it before ERP recording")
    payload = {"invoice_id": invoice.id, "amount": str(invoice.gross_amount), "currency": invoice.currency, "proposal_id": proposal.id}
    response = erp_adapter.create_vendor_bill_draft(payload, key) if mode == "draft" else erp_adapter.post_vendor_bill(payload, key)
    posting = ERPPosting(tenant_id=user.tenant_id, record_type="invoice", record_id=invoice.id, idempotency_key=key, mode=mode, status="success", external_reference=response["external_reference"], response=response)
    db.add(posting); invoice.status = InvoiceStatus.ERP_DRAFT if mode == "draft" else InvoiceStatus.POSTED
    audit(db, user, f"erp_{mode}", "invoice", invoice.id, after=response, origin="automation")
    return posting


def post_statement_to_erp(db: Session, statement: BankStatement, user: User, key: str) -> ERPPosting:
    existing = claim_idempotency(db, user, key, "bank_statement", statement.id, "post")
    if existing:
        return existing
    if statement.status != StatementStatus.VALIDATED:
        raise HTTPException(409, "Validated statement required")
    response = erp_adapter.post_bank_statement({"statement_id": statement.id}, key)
    posting = ERPPosting(tenant_id=user.tenant_id, record_type="bank_statement", record_id=statement.id, idempotency_key=key, mode="post", status="success", external_reference=response["external_reference"], response=response)
    db.add(posting); statement.status = StatementStatus.IMPORTED
    audit(db, user, "bank_statement_posted", "bank_statement", statement.id, after=response, origin="automation")
    return posting


def parse_bank_content(db: Session, statement: BankStatement, content: bytes, user: User) -> int:
    try:
        rows = parse_statement(content, statement.format)
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    count = 0
    for row in rows:
        tx_date = row["date"]
        amount = row["amount"]
        digest = hashlib.sha256(f"{user.tenant_id}|{tx_date}|{row['description']}|{amount}".encode()).hexdigest()
        duplicate = db.scalar(select(BankStatementLine).where(BankStatementLine.tenant_id == user.tenant_id, BankStatementLine.line_hash == digest))
        db.add(BankStatementLine(tenant_id=user.tenant_id, statement_id=statement.id, transaction_date=tx_date, value_date=row.get("value_date"), description=row["description"], reference=row.get("reference"), amount=amount, line_hash=digest, status="duplicate" if duplicate else "unallocated"))
        count += 1
    statement.status = StatementStatus.PARSED
    audit(db, user, "bank_statement_parsed", "bank_statement", statement.id, after={"lines": count}, origin="automation")
    return count
