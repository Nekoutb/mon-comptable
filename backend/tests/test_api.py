from decimal import Decimal
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.seed import seed
from app.services import normalize_invoice_number
from app.parsers import parse_camt053, parse_mt940


client = TestClient(app)


def token(email="nadia@akwa.example", password="DemoPass2026!"):
    seed()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_health_discloses_mock_integrations():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["erp"]["external_connection"] is False


def test_login_and_current_user():
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token()}"})
    assert response.status_code == 200
    assert response.json()["role"] == "accountant"


def test_invalid_login_is_rejected():
    seed()
    response = client.post("/api/v1/auth/login", json={"email": "nadia@akwa.example", "password": "WrongPassword"})
    assert response.status_code == 401


def test_invoice_number_normalization():
    assert normalize_invoice_number(" Fac-2026 / 0042 ") == "FAC20260042"


def test_invoice_upload_uses_mock_ocr_and_tenant_context():
    response = client.post(
        "/api/v1/invoices/upload",
        headers={"Authorization": f"Bearer {token()}"},
        files={"file": ("invoice.pdf", f"fictional invoice {uuid.uuid4()}".encode(), "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "XAF"
    assert Decimal(body["gross_amount"]) == Decimal("1428000.00")


def test_role_enforcement_blocks_accountant_approval():
    response = client.post(
        "/api/v1/invoices/not-a-real-id/approve",
        headers={"Authorization": f"Bearer {token()}"},
        json={"comment": "Not authorized"},
    )
    assert response.status_code == 403


def test_mt940_parser():
    rows = parse_mt940(b":20:REF\n:61:2608010801D1250,00NTRFABC123\n:86:Supplier payment\n")
    assert rows[0]["amount"] == Decimal("-1250.00")
    assert rows[0]["description"] == "Supplier payment"


def test_camt053_parser():
    xml = b"""<?xml version='1.0'?><Document><BkToCstmrStmt><Stmt><Ntry><Amt>500.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><BookgDt><Dt>2026-08-01</Dt></BookgDt><AcctSvcrRef>R1</AcctSvcrRef><AddtlNtryInf>Transfer</AddtlNtryInf></Ntry></Stmt></BkToCstmrStmt></Document>"""
    rows = parse_camt053(xml)
    assert rows[0]["amount"] == Decimal("500.00")


def test_inbound_email_rejects_bad_secret():
    response = client.post("/api/v1/inbound-email/webhook", headers={"X-Webhook-Secret": "wrong"}, json={"recipient": "invoices+akwa@example.com", "message_id": "msg-1"})
    assert response.status_code == 401
