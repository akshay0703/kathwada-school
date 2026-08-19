# API Specification

**Base URL:** `/api/v1/` (all endpoints below are relative to this).
**Auth:** Django session cookies (HttpOnly), CSRF token required on all
unsafe methods (POST/PUT/PATCH/DELETE) via `X-CSRFToken` header.

Auto-generated OpenAPI schema is available at `/api/v1/schema/` and
interactive docs at `/api/v1/docs/` (via `drf-spectacular`) once the server
is running — this file is the human-readable summary, the schema endpoint is
the executable source of truth once Phase 1+ adds real serializers.

## ✅ Implemented (Phase 0)

| Method | Path | Auth required | Purpose |
|---|---|---|---|
| GET | `/api/v1/health/` | No | Liveness + DB connectivity check. Returns `{"status": "ok\|degraded", "database": bool}`. |
| GET | `/api/v1/auth/csrf/` | No | Sets the `csrftoken` cookie; frontend calls this once before any unsafe request. |
| POST | `/api/v1/auth/login/` | No | `{"email", "password"}` → sets HttpOnly session cookie, returns the user profile. 401 with a generic message on failure (never reveals whether the email exists). |
| POST | `/api/v1/auth/logout/` | Yes | Clears the session server-side. |
| GET | `/api/v1/auth/me/` | Yes | Returns the current authenticated user (id, email, role, is_active, is_superuser, last_login_at). |
| GET | `/api/v1/auth/admin-stub/` | Yes (Admin role only) | **Scaffolding only, not a real feature** — exists solely to prove the `RolePermission` mechanism works end-to-end (see `permissions.md`). Delete this once a real admin-only endpoint exists in Phase 1. |

Note on status codes: DRF's `SessionAuthentication` returns **403** (not 401)
for anonymous requests to an authenticated-only endpoint, since no
`WWW-Authenticate` challenge scheme is configured. This is documented,
correct DRF behavior, not a bug — see the test docstrings in
`apps/accounts/tests/test_auth_flow.py`.

## 🔜 Planned (Phase 1+) — none of these exist yet

Grouped by the domain app that will own them (`architecture.md`'s app list).
Do not assume any of these work — they are listed here purely so a future
implementer knows the intended shape and doesn't have to re-derive it from
the ERD.

| App | Planned endpoints (indicative, not final) |
|---|---|
| `academics` | `/api/v1/academic-years/`, `/api/v1/classes/`, `/api/v1/sections/`, `/api/v1/class-sections/`, `/api/v1/subjects/` |
| `people` | `/api/v1/students/`, `/api/v1/teachers/`, `/api/v1/guardians/`, `/api/v1/teacher-assignments/` |
| `exams` | `/api/v1/exams/`, `/api/v1/exam-components/` |
| `marks` | `/api/v1/marks/` (bulk entry endpoints per class-section/exam-component likely needed — mirrors the prototype's per-test-tab entry workflow, see `prototype-analysis.md` §10) |
| `reportcards` | `/api/v1/report-cards/`, plus a `/publish/` action per the draft→publish workflow in `permissions.md` |
| `attendance` | `/api/v1/attendance/` |
| `fees` | `/api/v1/fee-structures/`, `/api/v1/fee-invoices/`, `/api/v1/fee-payments/` |
| `library` | `/api/v1/books/`, `/api/v1/book-copies/`, `/api/v1/book-issues/` |
| `documents` | `/api/v1/documents/` (upload/download via the S3-compatible storage backend) |
| `audit` | `/api/v1/audit-logs/` (read-only, Admin/Principal per `permissions.md`) |

Every planned endpoint above must, when built, declare `module_key` and
`permission_action_map`/`required_action` per the pattern already established in
`apps/accounts/permissions.py` (`HasModulePermission`) — no domain app should
invent its own bespoke permission-checking logic.
