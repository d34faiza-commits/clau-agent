// Panggilan API dari browser ke /api/* (diteruskan server Next.js ke backend). Request yang mengubah data
// membawa header CSRF dari /auth/me; error selalu berbentuk kontrak {error: {code, message}}.
export type Membership = { scope: string; role: string; max_level: string };
export type Me = {
  user: { id: number; display_name: string; email: string; memberships: Membership[]; mfa_enabled: boolean };
  mfa_required: boolean;
  must_change_password: boolean;
  next: "ready" | "password_change" | "mfa_setup";
  csrf_token: string;
};
export type ApiResult<T> = { ok: true; data: T } | { ok: false; status: number; code: string; message: string };

let csrf = "";

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<ApiResult<T>> {
  const method = init.method ?? "GET";
  const headers: Record<string, string> = { accept: "application/json" };
  if (init.body !== undefined) headers["content-type"] = "application/json";
  if (method !== "GET" && csrf) headers["x-csrf-token"] = csrf;
  let res: Response;
  try {
    res = await fetch(`/api/${path}`, { method, headers, body: init.body === undefined ? undefined : JSON.stringify(init.body), credentials: "same-origin", cache: "no-store" });
  } catch {
    return { ok: false, status: 0, code: "network_error", message: "Tidak ada koneksi ke server." };
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const err = (data as { error?: { code: string; message: string } } | null)?.error;
    return { ok: false, status: res.status, code: err?.code ?? "http_error", message: err?.message ?? `HTTP ${res.status}` };
  }
  if (data && typeof data === "object" && "csrf_token" in data) csrf = (data as Me).csrf_token;
  return { ok: true, data: data as T };
}

export function roleOf(me: Me): string {
  return me.user.memberships.find((m) => m.scope === "agency")?.role ?? me.user.memberships[0]?.role ?? "";
}

/** Tujuan setelah login: hanya path internal (cegah open redirect lewat ?next=). */
export function safeNext(raw: string | null): string {
  return raw && raw.startsWith("/") && !raw.startsWith("//") && !raw.startsWith("/api/") ? raw : "/";
}
