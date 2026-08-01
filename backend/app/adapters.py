from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Any


class ERPAdapter(ABC):
    @abstractmethod
    def health_check(self) -> dict: ...

    @abstractmethod
    def master_data(self) -> dict: ...

    @abstractmethod
    def create_vendor_bill_draft(self, payload: dict, idempotency_key: str) -> dict: ...

    @abstractmethod
    def post_vendor_bill(self, payload: dict, idempotency_key: str) -> dict: ...

    @abstractmethod
    def post_bank_statement(self, payload: dict, idempotency_key: str) -> dict: ...


class MockERPAdapter(ERPAdapter):
    """Deterministic local adapter. It never claims to contact an external ERP."""

    def health_check(self) -> dict:
        return {"ok": True, "provider": "mock", "external_connection": False}

    def master_data(self) -> dict:
        return {
            "accounts": [
                {"erp_id": "acc-401", "code": "401100", "name": "Fournisseurs", "type": "payable"},
                {"erp_id": "acc-624", "code": "624100", "name": "Entretien et réparations", "type": "expense"},
                {"erp_id": "acc-605", "code": "605300", "name": "Fournitures de bureau", "type": "expense"},
                {"erp_id": "acc-445", "code": "445200", "name": "TVA récupérable", "type": "tax"},
            ],
            "suppliers": [
                {"erp_id": "sup-001", "code": "FOU001", "name": "Africa Office SARL", "tax_id": "M012600001234A", "email": "billing@africa-office.example"},
                {"erp_id": "sup-002", "code": "FOU002", "name": "Clean & Care Services", "tax_id": "M012600009876B", "email": "invoices@clean-care.example"},
            ],
            "journals": [
                {"erp_id": "j-ap", "code": "ACH", "name": "Journal des achats", "kind": "purchase"},
                {"erp_id": "j-bank", "code": "BQ-AFB", "name": "Afriland First Bank", "kind": "bank"},
            ],
        }

    def _result(self, kind: str, key: str) -> dict:
        return {"success": True, "mocked": True, "external_reference": f"MOCK-{kind}-{key[-8:].upper()}", "message": "No external ERP was contacted"}

    def create_vendor_bill_draft(self, payload: dict, idempotency_key: str) -> dict:
        return self._result("DRAFT", idempotency_key)

    def post_vendor_bill(self, payload: dict, idempotency_key: str) -> dict:
        return self._result("BILL", idempotency_key)

    def post_bank_statement(self, payload: dict, idempotency_key: str) -> dict:
        return self._result("BANK", idempotency_key)


class OCRAdapter(ABC):
    @abstractmethod
    def extract(self, filename: str, content: bytes) -> dict[str, Any]: ...


class MockOCRAdapter(OCRAdapter):
    def extract(self, filename: str, content: bytes) -> dict[str, Any]:
        checksum_hint = sum(content[:256]) % 9000
        return {
            "provider": "mock",
            "external_processing": False,
            "supplier_name": "Africa Office SARL",
            "supplier_tax_id": "M012600001234A",
            "invoice_number": f"AO-{date.today().year}-{checksum_hint:04d}",
            "invoice_date": date.today().isoformat(),
            "currency": "XAF",
            "net_amount": "1200000.00",
            "tax_amount": "228000.00",
            "gross_amount": "1428000.00",
            "description": f"Office supplies extracted from {filename}",
            "confidence": Decimal("94.50"),
        }


erp_adapter = MockERPAdapter()
ocr_adapter = MockOCRAdapter()
