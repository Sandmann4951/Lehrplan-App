// Schlanker API-Client: Cookie-Sitzung, CSRF-Header, einheitliche Fehler.

export class ApiError extends Error {
  status: number;
  code: string;
  fieldErrors: Record<string, string>;
  body: Record<string, unknown>;

  constructor(status: number, body: Record<string, unknown>) {
    super(typeof body.message === "string" ? body.message : `Fehler ${status}`);
    this.status = status;
    this.code = typeof body.code === "string" ? body.code : "error";
    this.fieldErrors = (body.field_errors as Record<string, string>) ?? {};
    this.body = body;
  }
}

let csrfToken: string | null = null;
export function setCsrf(token: string | null) {
  csrfToken = token;
}

function readCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : null;
}

type Listener = () => void;
const unauthorizedListeners = new Set<Listener>();
export function onUnauthorized(fn: Listener) {
  unauthorizedListeners.add(fn);
  return () => {
    unauthorizedListeners.delete(fn);
  };
}

export type Query = Record<string, string | number | boolean | undefined | null | (string | number)[]>;

export function qs(params: Query): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, String(x)));
    else sp.append(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export async function api<T = any>(method: string, path: string, body?: unknown, query?: Query): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const init: RequestInit = { method, headers, credentials: "same-origin" };
  if (method !== "GET") {
    const token = csrfToken ?? readCookie("lp_csrf");
    if (token) headers["X-CSRF-Token"] = token;
  }
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  let res: Response;
  try {
    res = await fetch(`/api/v1${path}${query ? qs(query) : ""}`, init);
  } catch {
    throw new ApiError(0, { code: "network", message: "Server nicht erreichbar. Bitte Verbindung prüfen." });
  }
  if (res.status === 204) return undefined as T;
  let data: any = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text };
    }
  }
  if (!res.ok) {
    if (res.status === 401 && path !== "/auth/login") unauthorizedListeners.forEach((fn) => fn());
    throw new ApiError(res.status, data ?? {});
  }
  return data as T;
}

export const get = <T = any>(path: string, query?: Query) => api<T>("GET", path, undefined, query);
export const post = <T = any>(path: string, body?: unknown, query?: Query) => api<T>("POST", path, body ?? {}, query);
export const patch = <T = any>(path: string, body: unknown) => api<T>("PATCH", path, body);
export const put = <T = any>(path: string, body?: unknown) => api<T>("PUT", path, body ?? {});
export const del = <T = any>(path: string, query?: Query) => api<T>("DELETE", path, undefined, query);

export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    const fields = Object.values(e.fieldErrors);
    return fields.length ? `${e.message} ${fields.join(" ")}` : e.message;
  }
  return "Unbekannter Fehler.";
}
