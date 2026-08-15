const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

async function ensureCsrfCookie(): Promise<void> {
  if (getCookie("csrftoken")) return;
  await fetch(`${API_BASE_URL}/auth/csrf/`, { credentials: "include" });
}

export type CurrentUser = {
  id: number;
  email: string;
  role: string | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at: string | null;
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const isUnsafe = !["GET", "HEAD", "OPTIONS"].includes(method);

  if (isUnsafe) {
    await ensureCsrfCookie();
  }

  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (isUnsafe) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers.set("X-CSRFToken", csrfToken);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include", // send the HttpOnly session cookie
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // response had no JSON body — fall back to statusText
    }
    throw new Error(`${response.status}: ${detail}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<CurrentUser>("/auth/login/", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>("/auth/logout/", { method: "POST" }),
  me: () => request<CurrentUser>("/auth/me/"),
  health: () => request<{ status: string; database: boolean }>("/health/"),
};
