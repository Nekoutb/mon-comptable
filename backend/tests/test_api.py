from decimal import Decimal
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import ERPPosting, Tenant, User
from app.security import hash_password
from app.seed import seed
from app.services import claim_idempotency, normalize_invoice_number
from app.parsers import parse_camt053, parse_mt940


client = TestClient(app)


def token(email="nadia@akwa.example", password="DemoPass2026!", tenant="akwa"):
    seed()
    payload = {"email": email, "password": password}
    if tenant:
        payload["tenant"] = tenant
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    return response.json()["access_token"]


def auth(email="nadia@akwa.example", **kwargs):
    return {"Authorization": f"Bearer {token(email, **kwargs)}"}


def upload_invoice(headers, content=None):
    response = client.post(
        "/api/v1/invoices/upload",
        headers=headers,
        files={"file": ("invoice.pdf", content or f"fictional invoice {uuid.uuid4()}".encode(), "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()


def prepare_for_submit(headers, invoice_id):
    assert client.post(f"/api/v1/invoices/{invoice_id}/match-supplier", headers=headers).status_code == 200
    assert client.post(f"/api/v1/invoices/{invoice_id}/check-duplicate", headers=headers).status_code == 200
    assert client.post(f"/api/v1/invoices/{invoice_id}/generate-proposal", headers=headers).status_code == 200


def make_tenant(code=None):
    with SessionLocal() as db:
        tenant = Tenant(code=code or f"t{uuid.uuid4().hex[:8]}", name="Other Tenant")
        db.add(tenant)
        db.flush()
        user = User(tenant_id=tenant.id, email=f"user-{uuid.uuid4().hex[:8]}@other.example", name="Other User", role="accountant", password_hash=hash_password("DemoPass2026!"))
        db.add(user)
        db.commit()
        return tenant.id, tenant.code, user.email


def test_health_discloses_mock_integrations():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["erp"]["external_connection"] is False


def test_login_and_current_user():
    response = client.get("/api/v1/users/me", headers=auth())
    assert response.status_code == 200
    assert response.json()["role"] == "accountant"


def test_invalid_login_is_rejected():
    seed()
    response = client.post("/api/v1/auth/login", json={"email": "nadia@akwa.example", "password": "WrongPassword"})
    assert response.status_code == 401


def test_login_requires_tenant_code_when_email_is_ambiguous():
    seed()
    _, code, _ = make_tenant()
    with SessionLocal() as db:
        tenant_id = db.scalar(select(Tenant.id).where(Tenant.code == code))
        db.add(User(tenant_id=tenant_id, email="nadia@akwa.example", name="Homonym", role="accountant", password_hash=hash_password("DemoPass2026!")))
        db.commit()
    ambiguous = client.post("/api/v1/auth/login", json={"email": "nadia@akwa.example", "password": "DemoPass2026!"})
    assert ambiguous.status_code == 409
    scoped = client.post("/api/v1/auth/login", json={"email": "nadia@akwa.example", "password": "DemoPass2026!", "tenant": "akwa"})
    assert scoped.status_code == 200


def test_invoice_number_normalization():
    assert normalize_invoice_number(" Fac-2026 / 0042 ") == "FAC20260042"


def test_invoice_upload_uses_mock_ocr_and_tenant_context():
    body = upload_invoice(auth())
    assert body["currency"] == "XAF"
    assert Decimal(body["gross_amount"]) == Decimal("1428000.00")
    assert body["status"] == "review"


def test_invoice_upload_records_completed_background_job():
    headers = auth()
    invoice = upload_invoice(headers)
    jobs = client.get("/api/v1/admin/jobs", headers=auth("admin@akwa.example")).json()
    assert any(job["kind"] == "invoice_ocr" and job["record_id"] == invoice["id"] and job["status"] == "completed" for job in jobs)


def test_role_enforcement_blocks_accountant_approval():
    response = client.post(
        "/api/v1/invoices/not-a-real-id/approve",
        headers=auth(),
        json={"comment": "Not authorized"},
    )
    assert response.status_code == 403


def test_tenant_isolation_hides_other_tenants_invoices():
    invoice = upload_invoice(auth())
    _, other_code, other_email = make_tenant()
    other = auth(other_email, tenant=other_code)
    listed = client.get("/api/v1/invoices", headers=other).json()
    assert invoice["id"] not in {row["id"] for row in listed}
    patched = client.patch(f"/api/v1/invoices/{invoice['id']}", headers=other, json={"description": "hijack"})
    assert patched.status_code == 404


def test_full_ap_flow_and_locked_states():
    accountant = auth()
    invoice = upload_invoice(accountant)
    invoice_id = invoice["id"]
    prepare_for_submit(accountant, invoice_id)
    assert client.post(f"/api/v1/invoices/{invoice_id}/submit", headers=accountant).status_code == 200

    # Editing a submitted invoice is refused.
    locked = client.patch(f"/api/v1/invoices/{invoice_id}", headers=accountant, json={"gross_amount": "1.00"})
    assert locked.status_code == 409

    approver = auth("approver@akwa.example")
    assert client.post(f"/api/v1/invoices/{invoice_id}/approve", headers=approver, json={"comment": "ok"}).status_code == 200

    poster = auth("poster@akwa.example")
    draft_key = f"draft-{uuid.uuid4()}"
    draft = client.post(f"/api/v1/invoices/{invoice_id}/record-draft", headers={**poster, "Idempotency-Key": draft_key})
    assert draft.status_code == 200 and draft.json()["mocked"] is True
    post_key = f"post-{uuid.uuid4()}"
    posted = client.post(f"/api/v1/invoices/{invoice_id}/post", headers={**poster, "Idempotency-Key": post_key})
    assert posted.status_code == 200

    # Idempotent replay returns the original reference instead of double-posting.
    replay = client.post(f"/api/v1/invoices/{invoice_id}/post", headers={**poster, "Idempotency-Key": post_key})
    assert replay.status_code == 200
    assert replay.json()["external_reference"] == posted.json()["external_reference"]

    # A posted invoice can no longer be rejected, edited, or re-processed.
    assert client.post(f"/api/v1/invoices/{invoice_id}/reject", headers=approver, json={"comment": "too late"}).status_code == 409
    assert client.patch(f"/api/v1/invoices/{invoice_id}", headers=accountant, json={"description": "x"}).status_code == 409
    assert client.post(f"/api/v1/invoices/{invoice_id}/match-supplier", headers=accountant).status_code == 409
    assert client.post(f"/api/v1/invoices/{invoice_id}/generate-proposal", headers=accountant).status_code == 409
    assert client.post(f"/api/v1/invoices/{invoice_id}/submit", headers=accountant).status_code == 409


def test_reject_requires_pending_approval():
    accountant = auth()
    invoice = upload_invoice(accountant)
    response = client.post(f"/api/v1/invoices/{invoice['id']}/reject", headers=auth("approver@akwa.example"), json={"comment": "not pending"})
    assert response.status_code == 409


def test_amount_edit_invalidates_proposal():
    accountant = auth()
    invoice = upload_invoice(accountant)
    invoice_id = invoice["id"]
    prepare_for_submit(accountant, invoice_id)
    patched = client.patch(f"/api/v1/invoices/{invoice_id}", headers=accountant, json={"gross_amount": "999.99"})
    assert patched.status_code == 200
    blocked = client.post(f"/api/v1/invoices/{invoice_id}/submit", headers=accountant)
    assert blocked.status_code == 409
    assert "proposal" in blocked.json()["error"]["message"].lower()


def test_probable_duplicate_blocks_proposal():
    accountant = auth()
    first = upload_invoice(accountant)
    second = upload_invoice(accountant)
    shared_number = f"DUP-{uuid.uuid4().hex[:8]}"
    for invoice_id, amount in ((first["id"], "100.00"), (second["id"], "200.00")):
        assert client.patch(f"/api/v1/invoices/{invoice_id}", headers=accountant, json={"invoice_number": shared_number, "gross_amount": amount}).status_code == 200
        assert client.post(f"/api/v1/invoices/{invoice_id}/match-supplier", headers=accountant).status_code == 200
    check = client.post(f"/api/v1/invoices/{second['id']}/check-duplicate", headers=accountant)
    assert check.json() == {"level": "probable", "matched_invoice_id": first["id"], "posting_blocked": True}
    assert client.post(f"/api/v1/invoices/{second['id']}/generate-proposal", headers=accountant).status_code == 409


def test_idempotency_keys_are_tenant_scoped():
    seed()
    tenant_a, _, _ = make_tenant()
    tenant_b, _, _ = make_tenant()
    shared_key = f"key-{uuid.uuid4()}"
    with SessionLocal() as db:
        for tenant_id in (tenant_a, tenant_b):
            db.add(ERPPosting(tenant_id=tenant_id, record_type="invoice", record_id=str(uuid.uuid4()), idempotency_key=shared_key, mode="post", status="success"))
        db.commit()  # would raise IntegrityError with a globally-unique key
        user = db.scalar(select(User).where(User.tenant_id == tenant_a))
        assert claim_idempotency(db, user, shared_key, "invoice", db.scalar(select(ERPPosting.record_id).where(ERPPosting.tenant_id == tenant_a)), "post") is not None
        with pytest.raises(HTTPException) as exc:
            claim_idempotency(db, user, shared_key, "invoice", "another-record", "post")
        assert exc.value.status_code == 409


def test_mt940_parser():
    rows = parse_mt940(b":20:REF\n:61:2608010801D1250,00NTRFABC123\n:86:Supplier payment\n")
    assert rows[0]["amount"] == Decimal("-1250.00")
    assert rows[0]["description"] == "Supplier payment"


def test_camt053_parser():
    xml = b"""<?xml version='1.0'?><Document><BkToCstmrStmt><Stmt><Ntry><Amt>500.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><BookgDt><Dt>2026-08-01</Dt></BookgDt><AcctSvcrRef>R1</AcctSvcrRef><AddtlNtryInf>Transfer</AddtlNtryInf></Ntry></Stmt></BkToCstmrStmt></Document>"""
    rows = parse_camt053(xml)
    assert rows[0]["amount"] == Decimal("500.00")


def bank_journal_id(headers):
    journals = client.get("/api/v1/master-data/journals", headers=headers).json()
    return next(j["id"] for j in journals if j["kind"] == "bank")


def test_camt053_statement_flow_end_to_end():
    accountant = auth()
    journal = bank_journal_id(accountant)
    xml = f"""<?xml version='1.0'?><Document><BkToCstmrStmt><Stmt><Ntry><Amt>500.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><BookgDt><Dt>2026-08-01</Dt></BookgDt><AcctSvcrRef>{uuid.uuid4()}</AcctSvcrRef><AddtlNtryInf>Client payment</AddtlNtryInf></Ntry><Ntry><Amt>200.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><BookgDt><Dt>2026-08-01</Dt></BookgDt><AcctSvcrRef>{uuid.uuid4()}</AcctSvcrRef><AddtlNtryInf>Supplier payment</AddtlNtryInf></Ntry></Stmt></BkToCstmrStmt></Document>"""
    upload = client.post(
        f"/api/v1/bank-statements/upload?journal_id={journal}&opening_balance=100&closing_balance=400",
        headers=accountant,
        files={"file": (f"stmt-{uuid.uuid4().hex[:8]}.xml", xml.encode(), "application/xml")},
    )
    assert upload.status_code == 200, upload.text
    statement = upload.json()
    assert statement["format"] == "camt053"
    assert statement["status"] == "parsed"

    validated = client.post(f"/api/v1/bank-statements/{statement['id']}/validate", headers=accountant)
    assert validated.status_code == 200

    poster = auth("poster@akwa.example")
    key = f"stmt-{uuid.uuid4()}"
    posted = client.post(f"/api/v1/bank-statements/{statement['id']}/post", headers={**poster, "Idempotency-Key": key})
    assert posted.status_code == 200 and posted.json()["mocked"] is True
    replay = client.post(f"/api/v1/bank-statements/{statement['id']}/post", headers={**poster, "Idempotency-Key": key})
    assert replay.status_code == 200
    assert replay.json()["external_reference"] == posted.json()["external_reference"]


def test_mt940_statement_upload_with_octet_stream():
    accountant = auth()
    journal = bank_journal_id(accountant)
    body = f":20:REF-{uuid.uuid4().hex[:6]}\n:61:2608010801D1250,00NTRFABC123\n:86:Loyer bureau {uuid.uuid4().hex[:6]}\n"
    upload = client.post(
        f"/api/v1/bank-statements/upload?journal_id={journal}&opening_balance=2000&closing_balance=750",
        headers=accountant,
        files={"file": (f"stmt-{uuid.uuid4().hex[:8]}.mt940", body.encode(), "application/octet-stream")},
    )
    assert upload.status_code == 200, upload.text
    statement = upload.json()
    assert statement["format"] == "mt940"
    assert client.post(f"/api/v1/bank-statements/{statement['id']}/validate", headers=accountant).status_code == 200


def test_statement_upload_rejects_unknown_extension():
    accountant = auth()
    upload = client.post(
        "/api/v1/bank-statements/upload",
        headers=accountant,
        files={"file": ("statement.exe", b"MZ", "application/octet-stream")},
    )
    assert upload.status_code == 415


def test_unbalanced_statement_is_refused():
    accountant = auth()
    journal = bank_journal_id(accountant)
    csv_body = f"date,description,amount\n2026-08-01,Paiement {uuid.uuid4().hex[:6]},150.00\n"
    upload = client.post(
        f"/api/v1/bank-statements/upload?journal_id={journal}&opening_balance=0&closing_balance=999",
        headers=accountant,
        files={"file": (f"stmt-{uuid.uuid4().hex[:8]}.csv", csv_body.encode(), "text/csv")},
    )
    assert upload.status_code == 200
    response = client.post(f"/api/v1/bank-statements/{upload.json()['id']}/validate", headers=accountant)
    assert response.status_code == 422


def test_inbound_email_rejects_bad_secret():
    response = client.post("/api/v1/inbound-email/webhook", headers={"X-Webhook-Secret": "wrong"}, json={"recipient": "invoices+akwa@example.com", "message_id": "msg-1"})
    assert response.status_code == 401
