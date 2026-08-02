"""tenant-scoped idempotency keys

ERP posting idempotency keys were globally unique, so two tenants sending the
same key collided with an integrity error. Scope uniqueness to the tenant and
keep a plain index for lookups.

Revision ID: b7d31c9a54f2
Revises: edda78563138
"""
from alembic import op


revision = 'b7d31c9a54f2'
down_revision = 'edda78563138'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('erp_postings') as batch:
        batch.drop_constraint('erp_postings_idempotency_key_key', type_='unique')
        batch.create_unique_constraint('uq_erp_postings_tenant_idempotency', ['tenant_id', 'idempotency_key'])
        batch.create_index(op.f('ix_erp_postings_idempotency_key'), ['idempotency_key'], unique=False)


def downgrade():
    with op.batch_alter_table('erp_postings') as batch:
        batch.drop_index(op.f('ix_erp_postings_idempotency_key'))
        batch.drop_constraint('uq_erp_postings_tenant_idempotency', type_='unique')
        batch.create_unique_constraint('erp_postings_idempotency_key_key', ['idempotency_key'])
