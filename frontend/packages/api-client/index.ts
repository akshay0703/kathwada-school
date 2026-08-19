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

export type AcademicYear = {
  id: number;
  school: string;
  label: string;
  start_date: string; // "YYYY-MM-DD"
  end_date: string;
  is_current: boolean;
  created_at: string;
  updated_at: string;
};

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

// Thrown by request<T>() so callers can distinguish "the server explained
// what was wrong" (e.g. a 400 validation error) from a generic failure.
export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

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
    let body: unknown = null;
    let detail = response.statusText;
    try {
      body = await response.json();
      detail = extractErrorMessage(body) ?? detail;
    } catch {
      // response had no JSON body — fall back to statusText
    }
    throw new ApiError(response.status, body, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

// DRF error bodies vary in shape: {"detail": "..."} for permission/auth
// errors, {"field_name": ["msg"]} or {"non_field_errors": ["msg"]} for
// serializer validation errors. This normalizes all of them into one
// human-readable string for display.
function extractErrorMessage(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const obj = body as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  const messages: string[] = [];
  for (const [field, value] of Object.entries(obj)) {
    const text = Array.isArray(value) ? value.join(" ") : String(value);
    messages.push(field === "non_field_errors" ? text : `${field}: ${text}`);
  }
  return messages.length ? messages.join(" ") : null;
}

export const api = {
  login: (email: string, password: string) =>
    request<CurrentUser>("/auth/login/", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>("/auth/logout/", { method: "POST" }),
  me: () => request<CurrentUser>("/auth/me/"),
  health: () => request<{ status: string; database: boolean }>("/health/"),

  academicYears: {
    list: () => request<PaginatedResponse<AcademicYear>>("/academic-years/"),
    create: (data: Pick<AcademicYear, "label" | "start_date" | "end_date">) =>
      request<AcademicYear>("/academic-years/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Pick<AcademicYear, "label" | "start_date" | "end_date">>) =>
      request<AcademicYear>(`/academic-years/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/academic-years/${id}/`, { method: "DELETE" }),
    markCurrent: (id: number) => request<AcademicYear>(`/academic-years/${id}/mark-current/`, { method: "POST" }),
  },
};
