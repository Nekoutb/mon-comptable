from decimal import Decimal
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.seed import seed
from app.services import normalize_invoice_number


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
