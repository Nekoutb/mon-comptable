CREATE TABLE IF NOT EXISTS ap_invoice_documents (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  filename TEXT NOT NULL,
  content_type TEXT NOT NULL,
  byte_size INTEGER NOT NULL,
  sha256 TEXT NOT NULL,
  object_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'uploaded',
  extraction_json TEXT,
  proposal_json TEXT,
  odoo_move_id INTEGER,
  error_message TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ap_documents_owner_hash
ON ap_invoice_documents(owner_id, tenant_id, sha256);

CREATE INDEX IF NOT EXISTS idx_ap_documents_owner_created
ON ap_invoice_documents(owner_id, tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS ap_agent_runs (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  document_id TEXT NOT NULL,
  agent_name TEXT NOT NULL,
  model TEXT NOT NULL,
  status TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  output_json TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  FOREIGN KEY(document_id) REFERENCES ap_invoice_documents(id)
);

CREATE INDEX IF NOT EXISTS idx_ap_agent_runs_document
ON ap_agent_runs(owner_id, tenant_id, document_id, created_at DESC);

PRAGMA optimize;
