from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    tenant: str | None = Field(None, max_length=32, description="Tenant code, required when the email exists in several tenants")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class InvoiceUpdate(BaseModel):
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    currency: str | None = Field(None, min_length=3, max_length=3)
    net_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    gross_amount: Decimal | None = None
    description: str | None = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    entity_id: str
    supplier_id: str | None
    invoice_number: str | None
    invoice_date: date | None
    currency: str
    net_amount: Decimal
    tax_amount: Decimal
    gross_amount: Decimal
    status: str
    ocr_confidence: Decimal | None
    duplicate_level: str | None
    created_at: datetime


class ApprovalInput(BaseModel):
    comment: str | None = Field(None, max_length=2000)


class RejectInput(BaseModel):
    comment: str = Field(min_length=3, max_length=2000)


class StatementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    entity_id: str
    journal_id: str | None
    reference: str
    format: str
    currency: str
    opening_balance: Decimal
    closing_balance: Decimal
    status: str
    created_at: datetime
