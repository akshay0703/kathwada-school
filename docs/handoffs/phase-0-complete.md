PROJECT: Kathwada High School ERP

CURRENT PHASE:
Phase 0 complete, pending local Docker/infrastructure verification.

DO NOT:
- Rewrite architecture
- Replace Django
- Replace PostgreSQL
- Replace Next.js
- Change grading rules
- Start Phase 1 without approval

If you are a new Claude picking this project up: read docs/project-status.md
in full before doing anything else. It is the single source of truth and
supersedes any summary below if they ever disagree.

COMPLETED:
- Monorepo scaffold matching docs/architecture.md exactly (backend/apps/*,
  frontend/apps/*, frontend/packages/*, docker/, scripts/, docs/)
- Backend: apps/common (base models, health check), apps/accounts (User,
  Role, Module, RolePermission, session-auth views, HasModulePermission
  permission class, seed_permissions command), apps/audit (AuditLog +
  request-logging middleware)
- Frontend: packages/ui (design tokens extracted from the prototype, Button,
  globals.css), packages/api-client (cookie-based fetch wrapper with CSRF
  handling), apps/public-site (Home page + nav), apps/erp (login page +
  protected dashboard shell)
- docker/docker-compose.yml, backend.Dockerfile, frontend.Dockerfile,
  nginx.conf
- .github/workflows/ci.yml
- scripts/import_legacy_localstorage.py (dry-run migration parser, no DB
  writes) + sample fixture + tests
- Full docs/ set: architecture.md, database-schema.md, permissions.md,
  grading-engine.md, grading-engine-test-spec.md, api-spec.md,
  deployment.md, prototype-analysis.md (original prototype breakdown),
  decisions/0001-0003, this handoff

VERIFIED (actually executed, result observed):
- 0.1 Repo scaffold
- 0.3 Django bootstrap + /api/v1/health/ (pytest passed)
- 0.5 Custom email-based User model (superuser creation succeeded)
- 0.6 Session-cookie auth end-to-end (pytest passed + real curl round trip,
  localhost cross-origin only)
- 0.7 CORS/CSRF (real curl preflight + login from a genuinely different
  localhost origin, port 3001 -> port 8000)
- 0.8 Role/Permission scaffold (pytest passed: Student 403 / Admin 200 on
  identical stub endpoint)
- 0.9 ERP Next.js shell (next build succeeded, 5 static routes)
- 0.10 Public site shell (next build succeeded + curl'd live served HTML,
  confirmed branding present)
- 0.13 Legacy migration dry-run parser (ran against demo fixture: correct
  counts, zero issues; ran against a deliberately broken fixture: caught all
  4 injected defects)

CODE-COMPLETE (implementation exists, NOT runtime-verified against real
infrastructure):
- 0.2 Docker Compose skeleton — no Docker daemon was available to test with
- 0.4 PostgreSQL wiring — migrations verified against a temporary SQLite
  override only; checked-in settings default to Postgres everywhere
- 0.11 S3 storage — round trip verified via moto (mocked AWS S3 API only),
  never against a real MinIO container
- 0.12 CI pipeline — YAML valid, every step manually replayed locally and
  passed, but GitHub Actions itself has never run

NOT COMPLETE:
- 0.14 Deployment smoke test — depends entirely on 0.2, which is unverified
- Grading engine implementation itself (Phase 3) — only business rules
  (grading-engine.md) and a 30-case test spec (grading-engine-test-spec.md)
  exist; zero computation code
- Phase 1 domain apps (academics, people, exams, marks, reportcards,
  attendance, fees, library, documents) — empty scaffolding only, no models

KNOWN LIMITATIONS:
- Docker has NOT been runtime-tested in the current environment
- Real PostgreSQL integration has NOT been runtime-tested
- Real MinIO integration has NOT been runtime-tested
- GitHub Actions itself has NOT been executed
- Production HTTPS/domain-level cookie behavior has NOT been tested (only
  localhost:3001 -> localhost:8000, plain HTTP)
- Django resolved to version 6.1 during Phase 0 install rather than a strict
  5.x pin (recorded in architecture.md, not re-approved, not architecturally
  significant)

NEXT ACTION:
Run Docker verification locally: `cd docker && docker compose up --build`,
then work through the "Pending infrastructure verification" checklist in
docs/project-status.md (Postgres, MinIO, both frontends via nginx, CI on a
real PR, production-domain auth test once a staging domain exists).

AFTER DOCKER VERIFICATION:
Report the real results (including failures) back for review. Obtain final
Phase 0 sign-off only after docs/project-status.md's status table is updated
to reflect what was actually verified — then, and only then, begin Phase 1.

Phase 1 scope, when approved, is the domain apps listed under "NOT COMPLETE"
above, built against docs/database-schema.md and docs/permissions.md exactly
as documented. Phase 3 (grading engine) is built against
docs/grading-engine.md and docs/grading-engine-test-spec.md exactly as
documented — the compensatory aggregate pass rule (see ADR 0002) must not be
"corrected" into a stricter per-component rule.
