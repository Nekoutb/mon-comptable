/** Cloudflare Worker entry point for the vinext-starter template. */
import { handleImageOptimization, DEFAULT_DEVICE_SIZES, DEFAULT_IMAGE_SIZES } from "vinext/server/image-optimization";
import handler from "vinext/server/app-router-entry";

interface Env {
  ASSETS: Fetcher;
  DB: D1Database;
  IMAGES: {
    input(stream: ReadableStream): {
      transform(options: Record<string, unknown>): {
        output(options: { format: string; quality: number }): Promise<{ response(): Response }>;
      };
    };
  };
}

interface ExecutionContext {
  waitUntil(promise: Promise<unknown>): void;
  passThroughOnException(): void;
}

type OdooProtocol = "json2" | "jsonrpc" | "xmlrpc";

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {status, headers: {"content-type": "application/json; charset=utf-8", "cache-control": "no-store"}});
}

function safeOdooOrigin(value: string) {
  const url = new URL(value.trim());
  if (url.protocol !== "https:" || url.username || url.password || (url.port && url.port !== "443")) throw new Error("Use an HTTPS Odoo server URL without credentials or a custom port.");
  const host = url.hostname.toLowerCase();
  if (host === "localhost" || host.endsWith(".local") || /^127\.|^10\.|^192\.168\.|^169\.254\.|^0\./.test(host) || /^172\.(1[6-9]|2\d|3[01])\./.test(host)) throw new Error("Private or local server addresses are not allowed.");
  return url.origin;
}

async function odooError(response: Response) {
  const text = (await response.text()).slice(0, 4000);
  try {
    const value = JSON.parse(text) as {message?: string; error?: {message?: string; data?: {message?: string}}};
    return value.message || value.error?.data?.message || value.error?.message || `Odoo returned HTTP ${response.status}.`;
  } catch {
    return text.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 300) || `Odoo returned HTTP ${response.status}.`;
  }
}

async function testOdooConnection(request: Request) {
  if (request.method !== "POST") return json({ok: false, message: "Method not allowed."}, 405);
  let body: {endpoint?: string; database?: string; login?: string; api_key?: string; protocol?: OdooProtocol};
  try { body = await request.json(); } catch { return json({ok: false, message: "Invalid request body."}, 400); }
  if (!body.endpoint || !body.database || !body.api_key || !body.protocol) return json({ok: false, message: "Server URL, database, API key and protocol are required."}, 400);
  let origin: string;
  try { origin = safeOdooOrigin(body.endpoint); } catch (error) { return json({ok: false, message: error instanceof Error ? error.message : "Invalid Odoo URL."}, 400); }
  const headers = {"content-type": "application/json; charset=utf-8", "user-agent": "MyAccountant-Odoo-Connector/1.0"};
  try {
    if (body.protocol === "json2") {
      const response = await fetch(`${origin}/json/2/res.users/context_get`, {method: "POST", headers: {...headers, authorization: `bearer ${body.api_key}`, "x-odoo-database": body.database}, body: "{}"});
      if (!response.ok) return json({ok: false, protocol: body.protocol, message: await odooError(response), httpStatus: response.status}, response.status === 404 ? 422 : 401);
      const context = await response.json() as {uid?: number};
      return json({ok: true, protocol: body.protocol, uid: context.uid, message: "Authenticated successfully with Odoo JSON-2."});
    }
    if (!body.login) return json({ok: false, message: "Odoo login is required for the selected legacy protocol."}, 400);
    if (body.protocol === "jsonrpc") {
      const response = await fetch(`${origin}/jsonrpc`, {method: "POST", headers, body: JSON.stringify({jsonrpc: "2.0", method: "call", params: {service: "common", method: "authenticate", args: [body.database, body.login, body.api_key, {}]}, id: crypto.randomUUID()})});
      if (!response.ok) return json({ok: false, protocol: body.protocol, message: await odooError(response), httpStatus: response.status}, 401);
      const payload = await response.json() as {result?: number | false; error?: {message?: string; data?: {message?: string}}};
      if (!payload.result) return json({ok: false, protocol: body.protocol, message: payload.error?.data?.message || payload.error?.message || "Odoo rejected the database, login or API key."}, 401);
      return json({ok: true, protocol: body.protocol, uid: payload.result, message: "Authenticated successfully with Odoo JSON-RPC."});
    }
    const xml = `<?xml version="1.0"?><methodCall><methodName>authenticate</methodName><params><param><value><string>${body.database.replace(/[<>&]/g, "")}</string></value></param><param><value><string>${body.login.replace(/[<>&]/g, "")}</string></value></param><param><value><string>${body.api_key.replace(/[<>&]/g, "")}</string></value></param><param><value><struct/></value></param></params></methodCall>`;
    const response = await fetch(`${origin}/xmlrpc/2/common`, {method: "POST", headers: {...headers, "content-type": "text/xml"}, body: xml});
    const responseText = await response.text();
    const uid = Number(responseText.match(/<(?:int|i4)>(\d+)<\/(?:int|i4)>/)?.[1] || 0);
    if (!response.ok || !uid) return json({ok: false, protocol: body.protocol, message: responseText.includes("faultString") ? "Odoo XML-RPC rejected the database, login or API key." : `Odoo returned HTTP ${response.status}.`}, 401);
    return json({ok: true, protocol: body.protocol, uid, message: "Authenticated successfully with Odoo XML-RPC."});
  } catch {
    return json({ok: false, protocol: body.protocol, message: "The Odoo server could not be reached from the secure connector."}, 502);
  }
}

// Image security config. SVG sources with .svg extension auto-skip the
// optimization endpoint on the client side (served directly, no proxy).
// To route SVGs through the optimizer (with security headers), set
// dangerouslyAllowSVG: true in next.config.js and uncomment below:
// const imageConfig: ImageConfig = { dangerouslyAllowSVG: true };

const worker = {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/_vinext/image") {
      const allowedWidths = [...DEFAULT_DEVICE_SIZES, ...DEFAULT_IMAGE_SIZES];
      return handleImageOptimization(request, {
        fetchAsset: (path) => env.ASSETS.fetch(new Request(new URL(path, request.url))),
        transformImage: async (body, { width, format, quality }) => {
          const result = await env.IMAGES.input(body).transform(width > 0 ? { width } : {}).output({ format, quality });
          return result.response();
        },
      }, allowedWidths);
    }

    if (url.pathname === "/api/erp-connections/test") return testOdooConnection(request);

    return handler.fetch(request, env, ctx);
  },
};

export default worker;
