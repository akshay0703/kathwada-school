# Architecture — Approved & As Implemented

**Status:** Approved. Phase 0 (foundations) implemented against this exactly.
Any change to this document requires explicit approval — do not drift from it
based on convenience during implementation.

For the full original prototype analysis (17-point breakdown of the legacy
`kathwada-high-school.html` file) and the reasoning behind these choices, see
[`prototype-analysis.md`](prototype-analysis.md). This document is the
current, living summary — that one is the historical record of how we got
here.

For details broken out elsewhere (kept here only as pointers, not duplicated):
- Full ERD and entity descriptions → [`database-schema.md`](database-schema.md)
- Role/permission matrix → [`permissions.md`](permissions.md)
- Grading/ranking business rules → [`grading-engine.md`](grading-engine.md)
- API endpoints (implemented vs. planned) → [`api-spec.md`](api-spec.md)
- Docker/deployment → [`deployment.md`](deployment.md)
- Current build status → [`project-status.md`](project-status.md)

## Approved technology stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + React |
| Frontend structure | Two separate apps — `public-site` and `erp` — sharing a `packages/ui` design-system package and a `packages/api-client` package |
| Backend | Django 5 (installed as Django 6.1 in Phase 0 — see note below) + Django REST Framework |
| Database | PostgreSQL 16 |
| File storage | S3-compatible object storage (MinIO locally, AWS S3 or equivalent in production) |
| Authentication | Django session authentication — server-side sessions, HttpOnly + Secure cookies, never JWT-in-localStorage |
| API | REST, versioned under `/api/v1/` |
| Deployment | **Managed services**: Render (backend web service + both frontends as static sites) + Supabase (database + storage). GitHub Actions for CI. See [`deployment.md`](deployment.md) for the full Stage A/Stage B model. Docker remains in the repo for optional local development only — never required to deploy. |
| Reverse proxy | Not self-operated — Render and Supabase each terminate their own HTTPS/routing. `docker/nginx/` remains as part of the optional local Docker Compose setup only. |

**This list is closed.** Do not introduce Supabase, NestJS, Firebase,
JWT-in-localStorage, or any other replacement for the above without explicit
approval in a new conversation turn — a Claude picking this project back up
should treat the table above as fixed, not as a menu.

### One tracked version-pin deviation

The architecture was approved as "Django 5." The Phase 0 sandbox's package
index resolved `pip install django` to **Django 6.1** (the newest available
at build time) rather than pinning to the Django 5.x line. This is a version
number, not an architecture change — DRF/session-auth/ORM usage is unaffected
— but it's recorded here because it wasn't explicitly re-approved. If a strict
Django 5.x pin matters, downgrade `backend/requirements.txt` before Phase 1.

## Monorepo structure (as implemented)

```text
kathwada-school/
├── backend/
│   ├── config/                  # Django settings (base/dev/prod), urls, wsgi/asgi
│   └── apps/
│       ├── accounts/             # IMPLEMENTED — User, Role, Module, RolePermission, auth views
│       ├── audit/                 # IMPLEMENTED — AuditLog model + request-logging middleware
│       ├── common/                # IMPLEMENTED — TimeStampedModel, SoftDeleteModel, health check
│       ├── academics/             # scaffold only — no models yet (Phase 1: AcademicYear/Class/Section/Subject)
│       ├── people/                # scaffold only — no models yet (Phase 1: Student/Teacher/Guardian)
│       ├── exams/                 # scaffold only — no models yet (Phase 1: Exam/ExamComponent)
│       ├── marks/                 # scaffold only — no models yet (Phase 3: grading engine, see grading-engine.md)
│       ├── reportcards/           # scaffold only — no models yet
│       ├── attendance/            # scaffold only — no models yet
│       ├── fees/                  # scaffold only — no models yet
│       ├── library/               # scaffold only — no models yet
│       └── documents/             # scaffold only — no models yet
├── frontend/
│   ├── apps/
│   │   ├── public-site/            # IMPLEMENTED — Home page shell, nav
│   │   └── erp/                    # IMPLEMENTED — login page, protected dashboard shell
│   └── packages/
│       ├── ui/                     # IMPLEMENTED — design tokens, Button, globals.css
│       └── api-client/             # IMPLEMENTED — cookie-based fetch wrapper w/ CSRF handling
├── shared/
│   └── design-tokens/              # IMPLEMENTED — tokens.json, extracted verbatim from the prototype's CSS
├── docs/                            # this directory
├── docker/                          # docker-compose.yml + Dockerfiles + nginx.conf — CODE-COMPLETE, not runtime-verified
├── scripts/                         # IMPLEMENTED — legacy data dry-run migration parser + sample fixture
└── .github/workflows/ci.yml         # CODE-COMPLETE — YAML valid, every step manually replayed, GitHub Actions itself never run
```

Only `accounts`, `audit`, and `common` are wired into Django's
`INSTALLED_APPS` right now — this is intentional, not an oversight. The
remaining domain apps are empty directories awaiting Phase 1/3 models.

## Key architectural decisions baked into Phase 0

These are load-bearing and should not be silently changed by a future
implementer — see `docs/decisions/` for the full ADRs.

1. **Permissions are data, not code.** `Role` → `Module` → `RolePermission`
   are database rows (seeded via `manage.py seed_permissions`), checked by a
   single generic `HasModulePermission` DRF permission class. Adjusting who
   can do what is a data change, not a code change. See `permissions.md`.
2. **The Main Marksheet's compensatory aggregate pass rule is preserved
   exactly**, not "corrected" into a per-component pass requirement. See
   `grading-engine.md`.
3. **Multiple simultaneous class-sections are a first-class requirement**,
   unlike the prototype (which only ever handled one class at a time). See
   `database-schema.md`'s `ClassSection`/`Enrollment` design.
4. **Academic Year is first-class and historical data is never overwritten**
   on promotion — a new `Enrollment` row is added per year, old rows are
   never mutated. See `database-schema.md`.
