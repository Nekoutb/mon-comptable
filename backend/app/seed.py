from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select

from .adapters import erp_adapter
from .database import Base, SessionLocal, engine
from .models import Account, Journal, LegalEntity, Supplier, TaxCode, Tenant, User
from .security import hash_password


def seed() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(Tenant)):
            return
        tenant = Tenant(code="akwa", name="Akwa Consulting Group")
        db.add(tenant); db.flush()
        entity = LegalEntity(tenant_id=tenant.id, name="Akwa Consulting SARL", tax_id="M012600000001X")
        db.add(entity); db.flush()
        for email, name, role in [
            ("nadia@akwa.example", "Nadia Simo", "accountant"),
            ("approver@akwa.example", "Jean Etoa", "approver"),
            ("poster@akwa.example", "Marie Ndom", "poster"),
            ("admin@akwa.example", "Alice Mballa", "tenant_admin"),
        ]:
            db.add(User(tenant_id=tenant.id, email=email, name=name, role=role, password_hash=hash_password("DemoPass2026!")))
        master = erp_adapter.master_data()
        for row in master["accounts"]: db.add(Account(tenant_id=tenant.id, entity_id=entity.id, **row))
        for row in master["suppliers"]: db.add(Supplier(tenant_id=tenant.id, entity_id=entity.id, **row))
        for row in master["journals"]: db.add(Journal(tenant_id=tenant.id, entity_id=entity.id, currency="XAF", **row))
        db.add(TaxCode(tenant_id=tenant.id, entity_id=entity.id, code="TVA-REC", name="TVA récupérable — configuration de démonstration", rate=Decimal("19.25"), recoverable_percent=Decimal("100"), effective_from=date.today() - timedelta(days=365), active=True))
        db.commit()


if __name__ == "__main__":
    seed()
