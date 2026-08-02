export type ApiHealth = {
  status: string;
  version: string;
  erp: { ok: boolean; provider: string; external_connection: boolean };
  ocr: { provider: string; external_connection: boolean };
};

export type ApiMode = "connected" | "demo" | "checking";

export type SessionUser = { id: string; tenant_id: string; email: string; name: string; role: string };

export type ApiInvoice = {
  id: string;
  entity_id: string;
  supplier_id: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  currency: string;
  net_amount: string | number;
  tax_amount: string | number;
  gross_amount: string | number;
  status: string;
  ocr_confidence: string | number | null;
  duplicate_level: string | null;
  created_at: string;
};

export type ApiStatement = {
  id: string;
  entity_id: string;
  journal_id: string | null;
  reference: string;
  format: string;
  currency: string;
  opening_balance: string | number;
  closing_balance: string | number;
  status: string;
  created_at: string;
};

export type ApiSupplier = { id: string; name: string; code: string };

export type ApiDashboard = {
  accounts_payable: Record<string, number>;
  treasury: Record<string, number>;
  integrations: { erp: ApiHealth["erp"]; ocr: ApiHealth["ocr"] };
};

const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, "") ?? "";

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body?.error?.message ?? `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export async function getApiHealth(signal?: AbortSignal): Promise<ApiHealth | null> {
  if (!baseUrl) return null;
  const response = await fetch(`${baseUrl}/health`, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`API health check failed (${response.status})`);
  return response.json() as Promise<ApiHealth>;
}

export async function login(email: string, password: string, tenant?: string): Promise<string> {
  if (!baseUrl) throw new Error("NEXT_PUBLIC_API_URL is not configured");
  const response = await fetch(`${baseUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(tenant ? { email, password, tenant } : { email, password }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  const body = (await response.json()) as { access_token: string };
  return body.access_token;
}

export class AccountingApi {
  constructor(private token: string) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    if (!baseUrl) throw new Error("NEXT_PUBLIC_API_URL is not configured");
    const response = await fetch(`${baseUrl}/api/v1${path}`, {
      ...init,
      headers: { Accept: "application/json", Authorization: `Bearer ${this.token}`, ...init.headers },
    });
    if (!response.ok) throw new Error(await parseError(response));
    return (await response.json()) as T;
  }

  me() { return this.request<SessionUser>("/users/me"); }
  invoices() { return this.request<ApiInvoice[]>("/invoices"); }
  statements() { return this.request<ApiStatement[]>("/bank-statements"); }
  dashboard() { return this.request<ApiDashboard>("/dashboard"); }
  suppliers() { return this.request<ApiSupplier[]>("/master-data/suppliers"); }

  uploadInvoice(file: File) {
    const form = new FormData();
    form.append("file", file);
    return this.request<ApiInvoice>("/invoices/upload", { method: "POST", body: form });
  }
}
