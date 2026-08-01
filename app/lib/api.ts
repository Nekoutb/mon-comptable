export type ApiHealth = {
  status: string;
  version: string;
  erp: { ok: boolean; provider: string; external_connection: boolean };
  ocr: { provider: string; external_connection: boolean };
};

export type ApiMode = "connected" | "demo" | "checking";

const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, "") ?? "";

export async function getApiHealth(signal?: AbortSignal): Promise<ApiHealth | null> {
  if (!baseUrl) return null;
  const response = await fetch(`${baseUrl}/health`, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`API health check failed (${response.status})`);
  return response.json() as Promise<ApiHealth>;
}

export class AccountingApi {
  constructor(private token: string) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    if (!baseUrl) throw new Error("NEXT_PUBLIC_API_URL is not configured");
    const response = await fetch(`${baseUrl}/api/v1${path}`, {
      ...init,
      headers: { Accept: "application/json", Authorization: `Bearer ${this.token}`, ...init.headers },
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body?.error?.message ?? `Request failed (${response.status})`);
    return body as T;
  }

  invoices() { return this.request<Array<Record<string, unknown>>>("/invoices"); }
  statements() { return this.request<Array<Record<string, unknown>>>("/bank-statements"); }
  dashboard() { return this.request<Record<string, unknown>>("/dashboard"); }
  createInvoiceDraft(invoiceId: string, idempotencyKey: string) {
    return this.request<{ status: string; external_reference: string }>(`/invoices/${invoiceId}/record-draft`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    });
  }
}
