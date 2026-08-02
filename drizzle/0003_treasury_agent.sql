CREATE TABLE IF NOT EXISTS treasury_statements (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  journal_id INTEGER NOT NULL,
  journal_name TEXT NOT NULL,
  filename TEXT NOT NULL,
  object_key TEXT NOT NULL,
  transactions_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ready_for_review',
  odoo_line_ids_json TEXT,
  created_at TEXT NOT NULL,
  pushed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_treasury_owner_created ON treasury_statements(owner_id,tenant_id,created_at DESC);
PRAGMA optimize;
