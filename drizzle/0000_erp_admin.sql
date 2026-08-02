CREATE TABLE IF NOT EXISTS erp_connections (
  id TEXT PRIMARY KEY NOT NULL,
  owner_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  name TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  database_name TEXT NOT NULL,
  login TEXT NOT NULL,
  company TEXT NOT NULL,
  protocol TEXT NOT NULL,
  encrypted_key TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_sync_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_erp_connections_owner_tenant ON erp_connections(owner_id,tenant_id);
CREATE TABLE IF NOT EXISTS admin_tenants (
  id TEXT PRIMARY KEY NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS admin_agent_provisioning (
  id TEXT PRIMARY KEY NOT NULL,
  tenant_id TEXT NOT NULL,
  agent_code TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_provisioning_tenant_agent ON admin_agent_provisioning(tenant_id,agent_code);
