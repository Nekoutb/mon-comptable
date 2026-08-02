/** Cloudflare Worker entry point for the vinext-starter template. */
import { handleImageOptimization, DEFAULT_DEVICE_SIZES, DEFAULT_IMAGE_SIZES } from "vinext/server/image-optimization";
import handler from "vinext/server/app-router-entry";

interface Env {
  ASSETS: Fetcher;
  DB: D1Database;
  ERP_ENCRYPTION_KEY: string;
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

type StoredConnection={id:string;name:string;endpoint:string;database_name:string;login:string;company:string;protocol:OdooProtocol;encrypted_key:string;updated_at:string;last_sync_at:string|null};
function userId(request:Request){return request.headers.get("oai-authenticated-user-id")||""}
function bytesToBase64(bytes:Uint8Array){let value="";for(const byte of bytes)value+=String.fromCharCode(byte);return btoa(value)}
function base64ToBytes(value:string){return Uint8Array.from(atob(value),c=>c.charCodeAt(0))}
async function encryptionKey(secret:string){return crypto.subtle.importKey("raw",new TextEncoder().encode(secret.padEnd(32,"0").slice(0,32)),"AES-GCM",false,["encrypt","decrypt"])}
async function encrypt(value:string,secret:string){const iv=crypto.getRandomValues(new Uint8Array(12)),key=await encryptionKey(secret),encrypted=new Uint8Array(await crypto.subtle.encrypt({name:"AES-GCM",iv},key,new TextEncoder().encode(value)));return `${bytesToBase64(iv)}.${bytesToBase64(encrypted)}`}
async function decrypt(value:string,secret:string){const [iv,data]=value.split("."),key=await encryptionKey(secret),plain=await crypto.subtle.decrypt({name:"AES-GCM",iv:base64ToBytes(iv)},key,base64ToBytes(data));return new TextDecoder().decode(plain)}
async function getConnection(env:Env,owner:string){return env.DB.prepare("SELECT id,name,endpoint,database_name,login,company,protocol,encrypted_key,updated_at,last_sync_at FROM erp_connections WHERE owner_id=? AND tenant_id='default' LIMIT 1").bind(owner).first<StoredConnection>()}
function publicConnection(row:StoredConnection|null){return row?{id:row.id,name:row.name,endpoint:row.endpoint,database:row.database_name,login:row.login,company:row.company,protocol:row.protocol,updatedAt:row.updated_at,lastSyncAt:row.last_sync_at,connected:true}:null}
async function connectionApi(request:Request,env:Env){const owner=userId(request);if(!owner)return json({ok:false,message:"Sign in is required."},401);if(request.method==="GET")return json({ok:true,connection:publicConnection(await getConnection(env,owner))});if(request.method!=="POST")return json({ok:false,message:"Method not allowed."},405);let body:{name?:string;endpoint?:string;database?:string;login?:string;company?:string;protocol?:OdooProtocol;api_key?:string};try{body=await request.json()}catch{return json({ok:false,message:"Invalid request."},400)}if(!body.name||!body.endpoint||!body.database||!body.company||!body.protocol)return json({ok:false,message:"Complete every required connection field."},400);try{safeOdooOrigin(body.endpoint)}catch(error){return json({ok:false,message:error instanceof Error?error.message:"Invalid URL."},400)}const existing=await getConnection(env,owner);if(!body.api_key&&!existing)return json({ok:false,message:"API key is required for the first save."},400);const encrypted=body.api_key?await encrypt(body.api_key,env.ERP_ENCRYPTION_KEY):existing!.encrypted_key;const id=existing?.id||crypto.randomUUID(),now=new Date().toISOString();await env.DB.prepare("INSERT INTO erp_connections(id,owner_id,tenant_id,name,endpoint,database_name,login,company,protocol,encrypted_key,updated_at) VALUES(?,?,'default',?,?,?,?,?,?,?,?) ON CONFLICT(owner_id,tenant_id) DO UPDATE SET name=excluded.name,endpoint=excluded.endpoint,database_name=excluded.database_name,login=excluded.login,company=excluded.company,protocol=excluded.protocol,encrypted_key=excluded.encrypted_key,updated_at=excluded.updated_at").bind(id,owner,body.name,body.endpoint,body.database,body.login||"",body.company,body.protocol,encrypted,now).run();return json({ok:true,connection:publicConnection((await getConnection(env,owner))!),message:"ERP connection saved securely."})}
async function syncApi(request:Request,env:Env){const owner=userId(request);if(!owner)return json({ok:false,message:"Sign in is required."},401);const row=await getConnection(env,owner);if(!row)return json({ok:false,message:"Save an ERP connection before synchronising."},409);const key=await decrypt(row.encrypted_key,env.ERP_ENCRYPTION_KEY);const body={endpoint:row.endpoint,database:row.database_name,login:row.login,api_key:key,protocol:row.protocol};const testRequest=new Request(request.url,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body)}),tested=await testOdooConnection(testRequest),testedPayload=await tested.clone().json() as {ok?:boolean;message?:string};if(!testedPayload.ok)return json(testedPayload,tested.status);const refreshedAt=new Date().toISOString();await env.DB.prepare("UPDATE erp_connections SET last_sync_at=? WHERE id=?").bind(refreshedAt,row.id).run();return json({ok:true,message:"Application synchronised with Odoo.",refreshedAt,connection:publicConnection(row)})}

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

async function testOdooConnection(request: Request, env?: Env) {
  if (request.method !== "POST") return json({ok: false, message: "Method not allowed."}, 405);
  let body: {endpoint?: string; database?: string; login?: string; api_key?: string; protocol?: OdooProtocol};
  try { body = await request.json(); } catch { return json({ok: false, message: "Invalid request body."}, 400); }
  if (!body.api_key && env) {
    const saved = await getConnection(env, userId(request));
    if (saved) body = {endpoint:saved.endpoint,database:saved.database_name,login:saved.login,api_key:await decrypt(saved.encrypted_key,env.ERP_ENCRYPTION_KEY),protocol:saved.protocol};
  }
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

    if (url.pathname === "/api/erp-connections/test") return testOdooConnection(request,env);
    if (url.pathname === "/api/erp-connections") return connectionApi(request,env);
    if (url.pathname === "/api/sync") return syncApi(request,env);

    return handler.fetch(request, env, ctx);
  },
};

export default worker;
