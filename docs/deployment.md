# Deployment

**Status: CODE-COMPLETE, NOT RUNTIME VERIFIED.** Every file described below
(`render.yaml`, `build.sh`, static-export config, both frontend apps) has
been built and tested *locally* in this environment — static exports
actually run, `collectstatic` actually runs, the full backend test suite
actually passes. **No actual Render service, Supabase project, or DNS
record has been created.** Nothing here should be read as "the site is
live" — it means "everything needed to make it live has been prepared and
checked as thoroughly as possible without an internet-connected cloud
account." See `project-status.md` for the authoritative status table.

This project deploys to **managed services**, not a self-operated server.
You will never need to touch Docker, Linux, nginx, PostgreSQL
administration, or SSH to launch or update this site. Docker remains in the
repo (`docker/`) purely as an optional local-development convenience — it is
not part of the deployment path described here.

## The two stages

### Stage A — Free Demo

Goal: **₹0/month.** No real student data. Acceptable to have occasional cold
starts and an occasionally-paused database — there's nothing real at risk
yet.

### Stage B — Real School Production

Goal: **secure and reliable**, once actual students' names, marks,
attendance, fees, or documents go into the system. At that point, specific
free-tier behaviors (see the table below) stop being acceptable, not because
the free tier "doesn't work," but because unreachable-until-it-wakes-up and
no-backup-guarantee are not acceptable properties for a system holding
minors' academic records.

## Services, side by side

| Service | Stage A (Free/Demo) | Stage B (Production) | Why upgrade |
|---|---|---|---|
| **Public website** | Render Static Site — free, no sleep, no commercial-use restriction | Same — free tier is genuinely fine here permanently | Static files on a CDN don't get "more production-ready" by paying more |
| **ERP frontend** | Render Static Site — free, same as above | Same — free tier is fine, *as long as* the app stays fully client-rendered (see `architecture.md`'s caveat) | Same reasoning as the public site |
| **ERP backend (Django)** | Render free Web Service — sleeps after 15 min idle, ~30–60s cold start on the next request | Render **Starter, $7/month** — always on | A live ERP with staff logging in every morning and parents checking results cannot have a 30–60s wait on the first request of the day |
| **Database** | Supabase free PostgreSQL — 500MB, **may pause after 7 days with zero database activity** | Supabase **Pro, $25/month** — no auto-pause, daily backups, higher storage | Real student data must always be reachable, and must have a real backup guarantee — neither is true on the free tier |
| **File storage** | Supabase free Storage — 1GB, same pause behavior as the database (same project) | Included in Supabase Pro — 100GB | Same reasoning as the database (same underlying project) |

**No keep-alive workaround exists in this repository, deliberately.** The
free database pausing after a week of inactivity is documented, expected
behavior — not a problem to engineer around with artificial traffic. During
Stage A (testing/demo, no real data) a pause is a non-event: the next time
someone visits, Supabase wakes it back up automatically within a short
delay. The correct response to "this matters now" is moving to Stage B, not
generating fake requests to dodge it.

**Realistic Stage B recurring cost: ~$32/month (≈ ₹2,700/month)**, both
frontends still free. Domain registration/renewal is separate and is
whatever you pay your registrar — not estimated here.

## Automated development & deployment pipeline

**As of this update, routine deploys are fully automatic.** You no longer
open Render after a normal code change — this section explains exactly what
happens instead, and the one-time setup that made it possible.

### The flow

```
Claude writes code, tests it locally, commits, pushes to GitHub (main branch)
        ↓
GitHub Actions CI runs automatically:
  - backend: lint, migrate, migration-file check, tests, Django system check
  - frontend: lint, build both apps
  - migration-script: legacy-data parser tests
  - docker-build: confirms all three Docker images still build (dev parity)
        ↓
   all of the above passed?
        ↓ yes                              ↓ no
   deploy job fires the 3            STOPS HERE — nothing is deployed,
   Render "Deploy Hooks"             the failure is visible as a red ✕
        ↓                            on the GitHub Actions run
   Render builds & deploys
   each service independently
        ↓
   smoke-test job waits for the live
   URLs to respond, checks: backend
   health+DB, auth endpoint, public
   site, ERP site, sitemap, robots.txt
        ↓
   You open the live site and test the actual feature
```

### Why this is safe (the gate, explained)

Render's own "auto-deploy on every push" feature is turned **off**
(`autoDeploy: false` on all three services in `render.yaml`). The **only**
thing that can trigger a deploy now is GitHub Actions successfully POSTing to
a Render "Deploy Hook" URL — and that step (`deploy` job) is declared with
`needs: [backend, frontend, migration-script]`, so GitHub Actions itself
refuses to run it unless every one of those jobs already succeeded. A broken
build, a failing test, or an uncommitted migration file **cannot** reach
production — there's no path for it to.

### Migrations specifically

- Migrations run automatically, inside `backend/build.sh`, on every backend
  deploy — you never run one manually.
- `set -o errexit` at the top of `build.sh` means **if `migrate` fails, the
  entire build fails**, and Render's build-then-swap deployment model means
  the previously-live version keeps running — a failed migration can never
  take the live site down or leave it half-upgraded.
- CI additionally runs `python manage.py makemigrations --check --dry-run`
  before tests — this fails the build if any model change wasn't committed
  as an actual migration file, which is what guarantees "migration files
  must be committed to GitHub" rather than generated on the fly.
- Nothing in this pipeline ever runs `makemigrations` automatically in
  production, and nothing resets or seeds the production database — `migrate`
  only ever applies migration files that are already committed and reviewed.

### Why there's no automatic rollback

If a bad deploy included a database migration, reverting the *code* doesn't
undo that migration — the database schema stays changed either way. Building
an automatic rollback that's actually safe in every case isn't realistic, so
this pipeline deliberately doesn't attempt one. Instead, a failure is made
**loud and visible** (red ✕ on the GitHub Actions run, and/or a failed
`smoke-test` job), and the fix is a deliberate, informed decision — see
`emergency-operations.md`'s rollback section.

### One-time setup: Deploy Hooks + GitHub Secrets

This is a **one-time** setup, not something repeated per feature. Three
copy-paste steps in Render, three in GitHub.

**WHAT TO DO — repeat this once per service (3 times total: backend, public site, ERP)**
1. Open: the service's page in Render (e.g. `kathwada-erp-backend`)
2. Click: **"Settings"** in the sidebar
3. Select: scroll to find **"Deploy Hook"**, click **"Create Deploy Hook"** (or it may already show one)
4. Enter: nothing — copy the generated URL shown
5. Do NOT change: don't share this URL publicly — treat it like a password (anyone with it could trigger a deploy, though not access your data)
6. Expected result: a URL like `https://api.render.com/deploy/srv-xxxxx?key=yyyyy`

**WHAT TO DO — add each URL as a GitHub secret (3 times total)**
1. Open: `github.com/akshay0703/kathwada-school` → **"Settings"** tab (repo settings, not your account settings)
2. Click: **"Secrets and variables"** → **"Actions"** in the left sidebar
3. Click: **"New repository secret"**
4. Enter: **Name** — exactly one of `RENDER_DEPLOY_HOOK_BACKEND`, `RENDER_DEPLOY_HOOK_PUBLIC_SITE`, or `RENDER_DEPLOY_HOOK_ERP` (matching which service's hook you copied) — **Value** — paste the URL from the matching step above
5. Do NOT change: the exact secret names above — the CI workflow refers to them by these exact names
6. Expected result: after all three, the "Repository secrets" list shows all three names (values are always hidden, even from you, once saved — that's normal)

Once all three secrets exist, the pipeline described above is fully live —
the very next push to `main` that passes CI will deploy automatically.

## Repository layout for deployment

- `render.yaml` (repo root) — a Render **Blueprint**, used **once** to
  originally create the three services. After that one-time setup, editing
  this file does not change live service settings by itself — Render only
  re-reads it on an explicit "Manual Sync" (see Render's own Blueprint docs
  if you ever need that) or the very first creation. Ongoing deploys are
  driven by the CI pipeline above, not by this file changing.
- `.github/workflows/ci.yml` — the automated pipeline itself: lint, tests,
  builds, the migration-file guard, the CI-gated `deploy` job, and the
  post-deploy `smoke-test` job.
- `backend/build.sh` — what Render runs to build the backend: install
  dependencies, collect static files, run migrations, seed the permission
  matrix, and (idempotently, safely) ensure the first Admin account exists.
  You never run this yourself.
- `backend/config/settings/prod.py` — production Django settings: HTTPS
  enforcement, secure cookies (including the cross-site `SameSite=None`
  fix required by Render's per-service domain isolation — see
  `prototype-analysis.md`'s troubleshooting history if curious), HSTS,
  WhiteNoise-compressed static files.
- `frontend/apps/public-site/next.config.js` and
  `frontend/apps/erp/next.config.js` — both set `output: 'export'`, making
  each app a static site (a folder of plain HTML/CSS/JS) rather than a
  server that needs to keep running.

## Environment variables — exact list, exact source

Every variable below is referenced in `render.yaml` with a comment
explaining where its value comes from. This table is the same information,
grouped by service.

**`kathwada-erp-backend` (Django, Render Web Service):**

| Variable | Where the value comes from |
|---|---|
| `DJANGO_SETTINGS_MODULE` | Fixed value `config.settings.prod` — already set in `render.yaml`, nothing to do |
| `PYTHON_VERSION` | Fixed value — already set |
| `DJANGO_SECRET_KEY` | Render generates this automatically (`generateValue: true`) — you never see or type it |
| `DJANGO_ALLOWED_HOSTS` | The backend's own Render URL, e.g. `kathwada-erp-backend.onrender.com` (no `https://`, no trailing slash) |
| `CORS_ALLOWED_ORIGINS` | Both frontend URLs, comma-separated, e.g. `https://kathwada-public-site.onrender.com,https://kathwada-erp.onrender.com` |
| `CSRF_TRUSTED_ORIGINS` | Same two URLs as above |
| `DATABASE_URL` | From Supabase: **Project Settings → Database → Connection string** (choose the "URI" format, "Session pooler" mode) |
| `AWS_ACCESS_KEY_ID` | From Supabase: **Project Settings → Storage → S3 access keys** |
| `AWS_SECRET_ACCESS_KEY` | Same Supabase Storage panel as above |
| `AWS_STORAGE_BUCKET_NAME` | The bucket name you create in Supabase Storage, e.g. `kathwada-documents` |
| `AWS_S3_ENDPOINT_URL` | From Supabase: **Project Settings → Storage → S3 Connection → Endpoint** |
| `AWS_S3_REGION_NAME` | Same Supabase Storage S3 Connection panel, e.g. `ap-south-1` |
| `DJANGO_SUPERUSER_EMAIL` | Your real email — becomes the first Admin login |
| `DJANGO_SUPERUSER_PASSWORD` | A strong password you choose — see "Admin account management" below for what happens after |

**Admin account management.** `create_admin_from_env` (run automatically by
`build.sh` on every deploy) only ever *creates* the account if it doesn't
already exist — it never resets an existing user's password, so leaving
these two variables set in Render is safe indefinitely and does not "recreate
or overwrite" anything on subsequent deploys. Once you've confirmed you can
log in, you may optionally remove these two variables from Render (Settings
→ Environment) to reduce standing secret exposure — this is a hardening
step, not a requirement. **Every Admin/Principal/Teacher/Staff/Student/Parent
account after this first one should be created from inside the ERP itself**
(Phase 1+ user-management screens), never via environment variables — see
`permissions.md`.

**`kathwada-public-site` (Render Static Site):**

| Variable | Where the value comes from |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | The backend's URL + `/api/v1`, e.g. `https://kathwada-erp-backend.onrender.com/api/v1` |
| `NEXT_PUBLIC_ERP_URL` | The ERP static site's own URL, e.g. `https://kathwada-erp.onrender.com` |
| `NEXT_PUBLIC_SITE_URL` | This site's own URL — used to build the sitemap and canonical/Open Graph tags correctly |

**`kathwada-erp` (Render Static Site):**

| Variable | Where the value comes from |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Same backend URL as above |

None of these are secret except the Supabase database/storage credentials
and the auto-generated Django secret key — and Render's Blueprint flow
never asks you to paste those into a file, only into its own dashboard
fields (see the walkthrough below).

## Static ERP security — what's actually protecting student data

Because the ERP frontend is a static export (a folder of pre-built HTML
files on a CDN, not a server), it's worth being precise about what that
does and doesn't mean for security:

- The static HTML **shell** (page layout, login form, empty dashboard
  container) is public in the sense that it's a file anyone can download —
  the same as any website's HTML.
- **No student data, marks, attendance, fees, or documents are ever baked
  into that shell.** Every protected page fetches its real data from the
  Django API, after the page loads, using the authenticated session cookie.
  This was verified directly (see `project-status.md`'s evidence) by
  building the ERP app and inspecting the output: the dashboard page's
  built HTML contains no visible content at all until JavaScript runs and
  calls `/api/v1/auth/me/`.
- **Three independent layers keep this app out of Google, on top of that
  authentication boundary** (defense in depth, not a replacement for it):
  1. `robots: { index: false, follow: false }` in every page's metadata.
  2. `/robots.txt` disallowing every crawler from every path.
  3. An `X-Robots-Tag: noindex, nofollow` HTTP header, set via Render's
     dashboard-level static-site headers feature (`render.yaml`'s
     `headers:` block) — this exists specifically because static sites have
     no server process that could set a response header itself.
- **The actual security boundary is, and must remain, the Django backend.**
  Hiding the ERP from search engines stops it from being *discovered*; it
  does not and cannot stop someone with a direct URL from trying to reach
  it. That's what server-side session authentication and the
  `RolePermission` checks (`permissions.md`) are for — and those are
  unchanged by any of the deployment work described in this document.

## Exact launch sequence

**One-time setup (already completed):**
1. Render and Supabase accounts created.
2. Supabase project created (database + storage).
3. GitHub repository connected to Render via Blueprint — all three services
   created.
4. Environment variables entered directly in Render (never via this chat).
5. First deploy completed; Admin account created automatically via
   `DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD`.
6. Public site, ERP, and backend all confirmed live and working.
7. Deploy Hooks created in Render + added as GitHub Actions secrets (see
   "One-time setup" above) — this is what makes the flow below possible.

**Ongoing workflow, from now on:**
1. You ask for a feature. Claude builds it, tests it, commits, and pushes.
2. GitHub Actions runs CI automatically.
3. If CI passes, GitHub Actions triggers the three Render deploys
   automatically.
4. GitHub Actions waits for the live URLs to respond correctly
   (`smoke-test` job) and reports success or failure.
5. You open the live site and test the actual feature.

You do not repeat steps 1-7 above for future features — those were one-time
infrastructure setup. Buying a real domain later (add it in Render's
dashboard, no application code changes) and submitting to Google Search
Console (see below) remain the only two genuinely new one-off tasks ahead.

## WHAT I NEED TO DO — beginner-friendly account setup

These were the initial one-time steps (already completed) to set up the
underlying accounts. Kept here for reference / for setting up a second
environment (e.g. staging) later, not because you need to repeat them now.

**Create your Render account**
1. Open: [render.com](https://render.com)
2. Click: "Get Started"
3. Select: "Sign up with GitHub"
4. Enter: nothing else — authorize Render for your `kathwada-school`
   repository if it asks which repos to access
5. Do NOT change: any settings, and don't create a service yet
6. Expected result: you're logged into an empty Render dashboard

**Create your Supabase account**
1. Open: [supabase.com](https://supabase.com)
2. Click: "Start your project"
3. Select: "Sign up with GitHub"
4. Enter: nothing else yet
5. Do NOT change: don't create a project yet
6. Expected result: you're logged into an empty Supabase dashboard

The next steps — creating the actual Supabase project, connecting Render's
Blueprint, and pasting the environment variable values from the table above
— will be given in the same exact-click format once you're ready to
proceed.

## Google Search Console (after the site is live)

A step-by-step **Open → Click → Enter → Verify → Submit sitemap** guide will
be provided once there's a real, live URL to submit — submitting a sitemap
before the site exists has nothing to verify against. The mechanics are
already built and tested: `/sitemap.xml` and `/robots.txt` both generate
correctly from the public site (see `project-status.md`'s evidence), listing
exactly the seven real public pages and nothing from the ERP.

## What has actually been verified live, vs. what's new and not yet exercised

**Verified against real, live infrastructure (by you, directly):**

| Claim | Status |
|---|---|
| Render actually deploys this successfully | **VERIFIED** — all three services live |
| Supabase actually connects and serves data | **VERIFIED** — `/api/v1/health/` returns `"database":true` against the real Supabase Postgres instance |
| Public website live, all 7 pages, correct branding | **VERIFIED** |
| `sitemap.xml` / `robots.txt` live and correct | **VERIFIED** |
| ERP login works end-to-end (real session, real role) | **VERIFIED** — including diagnosing and fixing a real cross-site cookie issue along the way (`SameSite=None` fix, see `prod.py`) |
| First Admin account creation on the free tier (no Shell access) | **VERIFIED** — `create_admin_from_env` management command, idempotent, tested locally and confirmed working live |

**New in this update (CI-gated automated deploy pipeline) — CODE-COMPLETE, NOT YET RUNTIME VERIFIED:**

| Claim | Status |
|---|---|
| `makemigrations --check` guard blocks CI on uncommitted model changes | **Verified locally** (ran the exact command, confirmed "No changes detected" / correct exit code) — not yet seen actually blocking a real bad PR |
| `deploy` job only runs after backend+frontend+migration-script succeed | **Verified via YAML inspection** (`needs:` dependency confirmed) — not yet seen running for real (requires the one-time Deploy Hook + GitHub Secrets setup below, which hasn't happened yet) |
| `smoke-test` job correctly checks the live URLs | **Curl commands verified syntactically correct** against this project's real URLs, but blocked from executing end-to-end in this sandboxed environment specifically (its network egress only allows a small domain whitelist that doesn't include `onrender.com` — confirmed via the deny-reason header, not assumed) — will run for real the first time this pipeline actually fires |
| Render's `autoDeploy: false` actually stops independent deploys | **NOT YET VERIFIED** — requires watching a real push and confirming Render does *not* deploy on its own anymore |

The honest summary: the application-level deployment (the hard part — real
database, real auth, real live site) is proven. The new orchestration layer
on top of it (CI-gated deploys, automated smoke tests) is built and locally
verified wherever this environment allows, but its first real end-to-end run
hasn't happened yet — that happens the moment the one-time Deploy Hook setup
above is completed and the next code change is pushed.

