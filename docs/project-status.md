# Project Status — Single Source of Truth

**Last updated:** after (1) live deployment to real Render + Supabase
infrastructure was completed and personally verified by you, and (2) the
CI-gated automated deployment pipeline was built on top of it (see
"Live deployment status" and "Automated deployment pipeline status" below).
**If this document and any other document disagree, this document wins** —
update it whenever status changes.

## Current phase

**Phase 0 (Foundations) — complete and deployed to real, live infrastructure.**
Public website, ERP, and backend are all live on the internet, backed by a
real Supabase PostgreSQL database, with working authentication. An automated
CI-gated deployment pipeline has been built on top of this so that future
feature work (Phase 1+) does not require manual Render interaction — see
"Automated deployment pipeline status" below for exactly what's proven vs.
newly built.

Phase 1 has **not** started. Do not begin it without explicit approval.

## Live deployment status — personally verified by you, on real infrastructure

| Item | Status | Evidence |
|---|---|---|
| Django backend live | **VERIFIED** | `https://kathwada-erp-backend.onrender.com/api/v1/health/` reachable |
| Supabase PostgreSQL connection | **VERIFIED** | Health endpoint returns `"database":true`; required diagnosing and fixing a real password-URL-encoding issue along the way |
| Public website live, all pages | **VERIFIED** | All 7 pages load correctly with real branding |
| `sitemap.xml` / `robots.txt` live | **VERIFIED** | Correct content confirmed on the live URLs |
| ERP live, login works | **VERIFIED** | Required diagnosing and fixing a real cross-site session cookie issue (`SESSION_COOKIE_SAMESITE`/`CSRF_COOKIE_SAMESITE = "None"`, since Render isolates each service's subdomain as a separate "site") |
| Session persists, correct role returned | **VERIFIED** | Logged in as Admin, stayed authenticated, dashboard showed correct role |
| First Admin account creation (no Shell on free tier) | **VERIFIED** | `create_admin_from_env` management command, built specifically because Render's free Web Service plan has no Shell access |

This is real, not a simulation — three genuine bugs were found and fixed
during this process (a literal `[YOUR-PASSWORD]` placeholder that wasn't
substituted, Render's free tier lacking Shell access, and the cross-site
cookie issue), each diagnosed from actual error messages rather than guessed
at. See `deployment.md` for the technical detail on each fix.

## Phase 0 status — VERIFIED / CODE-COMPLETE / NOT COMPLETE

Definitions (do not blur these):
- **VERIFIED** — actually executed in this environment and the result was
  observed to pass.
- **CODE-COMPLETE** — the implementation/config exists and was reviewed, but
  could not be executed against real infrastructure in this environment.
- **NOT COMPLETE** — does not exist or depends entirely on something that's
  NOT COMPLETE.

| ID | Task | Status |
|---|---|---|
| 0.1 | Repo scaffold | **VERIFIED** |
| 0.2 | Docker Compose skeleton | **CODE-COMPLETE** |
| 0.3 | Django bootstrap + health endpoint | **VERIFIED** |
| 0.4 | PostgreSQL wiring, idempotent migrations | **CODE-COMPLETE** (migration mechanics verified against SQLite substitute; never run against real Postgres) |
| 0.5 | Custom email-based User model | **VERIFIED** |
| 0.6 | Session-cookie auth end-to-end | **VERIFIED** (localhost cross-origin; production domain/HTTPS not tested — see below) |
| 0.7 | CORS/CSRF cross-subdomain | **VERIFIED** (localhost cross-origin only — see below) |
| 0.8 | Role/Permission scaffold | **VERIFIED** |
| 0.9 | ERP Next.js shell | **VERIFIED** (build + real HTTP serve; no manual browser click-through) |
| 0.10 | Public site shell | **VERIFIED** |
| 0.11 | S3-compatible storage | **CODE-COMPLETE** (moto-mocked round trip VERIFIED; real MinIO never run) |
| 0.12 | CI pipeline | **CODE-COMPLETE** (YAML valid, every step manually replayed and passed; GitHub Actions itself never executed) |
| 0.13 | Legacy data migration dry-run parser | **VERIFIED** |
| 0.14 | Deployment smoke test | **NOT COMPLETE** (depends entirely on 0.2) |

**8 VERIFIED · 5 CODE-COMPLETE · 1 NOT COMPLETE.**

## Automated deployment pipeline status (this update)

Built in response to: manual Render/GitHub/Supabase operation being
unsustainable per-feature. Goal: Claude develops → tests → commits → pushes
→ CI validates → automatic deploy → you test the live feature, with zero
manual Render interaction for routine changes.

**PROVEN END-TO-END, for real, on GitHub's actual servers** — not simulated,
not assumed. Run [`#5`](https://github.com/akshay0703/kathwada-school/actions),
commit `994773d`, "Fix doubled apps/ path in frontend.Dockerfile": all six
jobs green, total duration 2m 24s. `deploy` fired all three Render Deploy
Hooks (5s), `smoke-test` then waited for and confirmed the real live site
actually works (1m 24s of polling). This is the single most important
verification in this document — everything below it was true before this
run; this run is what makes "the automated pipeline works" a demonstrated
fact rather than a design.

**Also genuinely useful:** this same run is what caught a real bug — the
first-ever real `docker-build` run (Phase 0's version had never actually
executed on a machine with a Docker daemon) found a doubled `apps/apps/...`
path in `docker/frontend.Dockerfile` that had been silently wrong since
Phase 0. Fixed in commit `994773d`. This is exactly the kind of thing the
pipeline is supposed to catch, catching it correctly, immediately, on the
very first real opportunity.

| Item | Status | Evidence |
|---|---|---|
| `makemigrations --check` CI guard | **VERIFIED** | Passed as part of the green `backend` job in run #5, on real GitHub infrastructure |
| `deploy` job only runs after backend+frontend+migration-script succeed | **VERIFIED** | Confirmed both structurally (`needs:`) and by the actual dependency graph in run #5 |
| `smoke-test` job correctly checks the live URLs | **VERIFIED** | Ran for real in run #5, passed, 1m 24s of real polling against the real live site |
| Render's `autoDeploy: false` stops independent deploys | **VERIFIED** | The only deploy trigger in run #5 was the CI-fired Deploy Hooks — Render did not deploy independently |
| Deploy Hooks + GitHub Secrets one-time setup | **COMPLETE** | All 3 hooks created, all 3 secrets added, confirmed working in run #5 |
| First real end-to-end automated deploy | **VERIFIED** | Run #5, in full |

## Deployment preparation status (Render + Supabase managed-services model)

Approved direction: replace self-operated Docker/nginx/Postgres/MinIO with
Render (2 static sites + 1 web service) and Supabase (database + storage).
See `deployment.md` for the full model. This is infrastructure preparation,
not a Phase 0 checklist item and not Phase 1 — no domain features were
built.

| Area | Status | Evidence |
|---|---|---|
| Backend Render configuration | **CODE-COMPLETE** | `render.yaml`, `backend/build.sh`, WhiteNoise wired into `prod.py`. `manage.py check --deploy` passes (only expected warnings). `collectstatic` actually runs, produces manifest output. |
| Public static export | **VERIFIED** | `next.config.js` sets `output: 'export'`; actually built — `npm run build --workspace=apps/public-site` succeeds, all 7 routes + sitemap + robots present in `out/`. |
| ERP static export | **VERIFIED** | Same — `npm run build --workspace=apps/erp` succeeds, login/dashboard/robots.txt all present in `out/`. Root page's redirect logic was found to behave unpredictably under static export and was fixed to an explicit client-side redirect before this was confirmed working. |
| Public pages (About/Academics/Admissions/Gallery/News/Contact) | **VERIFIED** | All 6 built using real content extracted from the original prototype (see `prototype-analysis.md`); genuinely-unverified details (phone, staff names, exact dates) explicitly marked `[PLACEHOLDER]`, not invented. |
| SEO (titles/descriptions/canonical/OG/JSON-LD/heading hierarchy) | **VERIFIED** | Directly inspected the built HTML: unique `<title>`/description/canonical/OG per page (7/7), exactly one `<h1>` per page (7/7), zero broken internal links, `EducationalOrganization` JSON-LD present on Home with only real/non-placeholder-pattern fields included. A title-templating bug was found during this check (Home page's title wasn't inheriting the layout template) and fixed by switching every page to an explicit full title string. |
| Sitemap | **VERIFIED** | `sitemap.xml` inspected directly — exactly the 7 real public routes, zero ERP routes (structurally impossible for them to appear, since the ERP is a separate app entirely). |
| Public robots.txt | **VERIFIED** | Inspected directly — allows all crawlers, correct sitemap URL. |
| ERP noindex (3 layers) | **VERIFIED (layers 1–2) / CODE-COMPLETE (layer 3)** | Layer 1 (`robots: noindex` meta tag) and layer 2 (`/robots.txt` disallow-all) confirmed present in built HTML on all 3 ERP pages. Layer 3 (`X-Robots-Tag` header) is configured in `render.yaml` via Render's dashboard-level static-site headers feature — this cannot be confirmed by inspecting build output (it's not a file, it's a server response header Render adds), so it remains unverified until actually deployed. |
| Static-data security audit | **VERIFIED** | Full `grep` sweep of every file in the ERP's built output for password/secret/API-key/database-URL/AWS-key patterns and email addresses. Only matches found were generic library code (URL-parsing polyfills, React's input-type list) and our own login form's field labels/generic error text — zero real secrets, zero real user data. Directly confirmed the dashboard page's server-rendered HTML shell has **zero visible content** before JavaScript runs. |
| Supabase storage configuration | **CODE-COMPLETE** | Existing `django-storages`/boto3 config from Phase 0 requires zero code changes — only different env var *values* (Supabase's S3-compatible endpoint). Cannot be runtime-verified without an actual Supabase project. |
| Render configuration | **CODE-COMPLETE** | `render.yaml` is valid YAML, defines all 3 services correctly per Render's documented Blueprint schema. Cannot be runtime-verified without an actual Render account. |
| Existing tests (post-deployment-prep) | **VERIFIED** | Full backend suite re-run after all changes: 9/9 passed under dev settings (same settings CI uses); `ruff check` clean; migrations idempotent (fresh + re-run). Additionally ran `check --deploy`, `collectstatic`, and `migrate` under **prod** settings — all passed. Re-running the full auth-flow suite under prod settings produces expected 301 HTTPS redirects (`SECURE_SSL_REDIRECT=True` working as designed against a test client that doesn't simulate TLS) — this is correct behavior, not a failure, and prod security was not weakened to avoid it. |
| Documentation | **VERIFIED** | `deployment.md` rewritten with Stage A/B tables, exact env vars, beginner-friendly account-setup steps. `architecture.md` updated for consistency (Docker relabeled dev-only/optional). All internal doc links re-checked, resolve correctly. |

**External verification still required (cannot be done from this
environment — see `deployment.md`'s own status table):** actual Render
deployment, actual Supabase connection, actual production HTTPS, actual DNS,
actual GitHub Actions execution, actual cloud-to-cloud communication between
Render and Supabase. None of these are claimed as verified anywhere in this
document.

## Known environment limitations (explicitly recorded, do not silently forget these)

- **Docker has NOT been runtime-tested.** No Docker daemon was available in
  the Phase 0 build environment. `docker compose up` has never been run.
- **Real PostgreSQL integration has NOT been runtime-tested.** All migration
  runs, model tests, and auth-flow tests used a temporary SQLite override
  (never committed — checked-in settings default to Postgres everywhere).
- **Real MinIO integration has NOT been runtime-tested.** The only storage
  test uses `moto` (mocked AWS S3 API), which proves the django-storages/
  boto3 code path is correct but does not touch a real MinIO container or
  the Docker network.
- **GitHub Actions itself has NOT been executed.** `.github/workflows/ci.yml`
  is YAML-valid and every step was manually replayed locally with passing
  results, but no real GitHub Actions run has ever happened.
- **Production HTTPS/domain cookie behavior has NOT been tested.** The
  verified cross-origin auth test was `localhost:3001` → `localhost:8000`
  (plain HTTP, both localhost) — real evidence the CORS/CSRF/cookie
  *mechanism* works, but not evidence for `erp.kathwadahighschool.edu.in`
  with real TLS.
- **The grading engine itself has NOT been implemented.** Only its business
  rules (`grading-engine.md`) and acceptance test specification
  (`grading-engine-test-spec.md`, 30 cases) exist. No `marks`/`reportcards`
  models, no computation code.

None of the above should ever be described as "production-verified" until
each is individually re-tested against real infrastructure and this table is
updated to reflect it.

## Current architecture

See [`architecture.md`](architecture.md) for the full approved stack and
structure. Summary: Next.js + TypeScript + React (two apps: public-site,
erp) · Django 5 (installed as 6.1, see note in architecture.md) + DRF ·
PostgreSQL 16 · S3-compatible storage · Django session auth with
HttpOnly/Secure cookies · REST API under `/api/v1/` · Docker · GitHub Actions
· nginx.

This stack is **approved and closed** — do not introduce Supabase, NestJS,
Firebase, JWT-in-localStorage, or any replacement without a new, explicit
approval.

## Completed files/modules

- **Backend:** `config/` (settings split, urls, wsgi/asgi) · `apps/common`
  (base models, health check, exception handler) · `apps/accounts` (User,
  Role, Module, RolePermission, session auth views, `HasModulePermission`,
  `seed_permissions` and `create_admin_from_env` management commands) ·
  `apps/audit` (AuditLog model + request-logging middleware). Domain apps
  (`academics`, `people`, `exams`, `marks`, `reportcards`, `attendance`,
  `fees`, `library`, `documents`) exist as empty scaffolding only — no models.
- **Frontend:** `packages/ui` (design tokens extracted verbatim from the
  prototype's CSS, Button, globals.css) · `packages/api-client` (cookie-based
  fetch wrapper with CSRF handling) · `apps/public-site` (Home page, nav
  shell) · `apps/erp` (login page, protected dashboard shell).
- **Infra:** `docker/` (compose file, two Dockerfiles, nginx config) ·
  `.github/workflows/ci.yml`.
- **Scripts:** `scripts/import_legacy_localstorage.py` (dry-run parser) +
  `scripts/sample_data/khs_erp_data_v1.demo.json` + tests.
- **Docs:** this file, plus `architecture.md`, `database-schema.md`,
  `permissions.md`, `grading-engine.md`, `grading-engine-test-spec.md`,
  `api-spec.md`, `deployment.md`, `emergency-operations.md`,
  `prototype-analysis.md` (original 17-point prototype breakdown),
  `decisions/`, `handoffs/`.

## Pending infrastructure verification (the actual next steps, in order)

1. `docker compose up --build` from a clean checkout — does the composed
   stack actually come up?
2. Confirm backend ↔ real Postgres (not SQLite).
3. Confirm backend ↔ real MinIO over the Docker network — real upload/
   download/delete, not `moto`.
4. Confirm both Next.js apps are reachable through nginx.
5. Push a branch / open a PR to confirm GitHub Actions actually runs and
   passes for real.
6. Once a staging domain + TLS exist, re-test the auth/CORS/CSRF flow at the
   domain level, not just localhost.

## Approved decisions (do not revisit without explicit new approval)

1. Technology stack per `architecture.md` — closed list, no substitutions.
2. No real legacy student data exists to migrate yet; the migration script
   is validated against demo data only and is kept, not discarded, for when
   real data is provided.
3. The Main Marksheet's compensatory aggregate pass rule is preserved
   exactly — see `grading-engine.md`. Individual FST/SST/UT1/UT2/Main test
   results keep their own separate (non-compensatory, per-subject-gate)
   pass rules.
4. Six roles (Admin/Principal/Teacher/Staff/Student/Parent), the permission
   matrix in `permissions.md` as a starting point, and the draft→publish
   workflow for marks/report cards.
5. Multiple simultaneous class-sections are required in production
   (Std 8-A/8-B/9-A/9-B/10-A/10-B etc.), unlike the prototype.
6. Academic Year is first-class; historical data is never overwritten on
   promotion — see `database-schema.md`.
7. Permissions are enforced via a data-driven `RolePermission` table, not
   hardcoded checks, so they're adjustable later without a rewrite.

## Open decisions (need your input before the relevant Phase)

1. Whether production should preserve or change the prototype's behavior of
   treating a blank mark identically to a mark of zero (`EDGE-03` in
   `grading-engine-test-spec.md`) — flagged, not resolved.
2. Exact API endpoint shapes for Phase 1+ domain apps (`api-spec.md`'s
   "Planned" table is indicative, not final — needs review when each app is
   actually built).
3. Strict Django 5.x vs. the Django 6.1 that was actually installed in
   Phase 0 (see the version-pin note in `architecture.md`) — not
   architecturally significant, but not explicitly re-approved either.
4. All real contact details (`[PLACEHOLDER]` markers throughout the public
   site — phone number, email address, staff names, some historical dates)
   need to be supplied by you before the public site is genuinely ready to
   launch, per `deployment.md`.

## Exact next step

**The automated pipeline is fully set up and proven working end-to-end**
(see "Automated deployment pipeline status" above — run #5, all green).
Nothing further is required to make future feature development flow
automatically: Claude builds → tests → pushes → CI validates → deploys →
you test live.

**Phase 1** (the first real domain feature — see `database-schema.md` for
what's approved) can begin on your explicit go-ahead. See
`handoffs/phase-0-deployment-automation-complete.md` for the condensed
version of this whole document meant to survive a context reset — this file
(`project-status.md`) is always the current source of truth if they disagree.
