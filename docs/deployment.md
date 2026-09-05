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

## Repository layout for deployment

- `render.yaml` (repo root) — a Render **Blueprint**. Connecting this repo to
  Render and choosing "New Blueprint Instance" reads this file and creates
  all three services in one step, with every secret value left blank for you
  to fill in (see "Environment variables" below) — nothing secret is ever
  committed.
- `backend/build.sh` — what Render runs to build the backend: install
  dependencies, collect static files, run migrations. You never run this
  yourself.
- `backend/config/settings/prod.py` — production Django settings: HTTPS
  enforcement, secure cookies, HSTS, WhiteNoise-compressed static files.
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
| `DJANGO_SUPERUSER_EMAIL` | Pick the email for the first Admin login — this account is created automatically on first deploy (see "First login" below) |
| `DJANGO_SUPERUSER_PASSWORD` | Pick a strong password for that same account — change it after first login if you'd rather not leave it in Render's dashboard long-term |

**First login:** on first deploy, `build.sh` runs `create_admin_from_env`,
which creates exactly one Admin superuser from the two variables above (and
does nothing if they're unset). On every later deploy it leaves that account
alone — it will never reset the password or create a duplicate. If you ever
need to reset a forgotten password, add a *third*, temporary variable,
`DJANGO_SUPERUSER_RESET_PASSWORD=true`, redeploy once, confirm you can log
in, then delete that variable again — leaving it set would silently reset
the password back to `DJANGO_SUPERUSER_PASSWORD` on every future deploy.

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

1. **You** create free accounts on Render and Supabase (both support
   "Sign up with GitHub" — no separate password to manage).
2. **You** create a Supabase project — this gives you both the database and
   file storage together.
3. **You** copy a small number of values from Supabase's dashboard into
   Render's dashboard when prompted (exact fields listed above).
4. **You** connect this GitHub repository to Render and choose "New
   Blueprint Instance" — Render reads `render.yaml` and creates all three
   services automatically.
5. Render builds and deploys all three services. This takes a few minutes;
   you watch progress in Render's dashboard, no action needed.
6. **You** run one command Render gives you a button for (or a documented
   one-line management command) to create the first Admin login.
7. Open the public site, open the ERP, log in — confirms everything is
   wired correctly.
8. Whenever you buy a real domain: add it in Render's dashboard (exact DNS
   values will be provided at that time) — no application code changes.
9. Submit the site to Google Search Console (see below).

## WHAT I NEED TO DO — beginner-friendly account setup

These are the only two things to do right now. Everything else happens
after these accounts exist and Claude has confirmed the repository is ready.

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

## What this environment could and couldn't verify

| Claim | Status |
|---|---|
| Both frontend apps build as static exports | **Verified** — actually built, output inspected |
| `sitemap.xml` / `robots.txt` generate with correct content | **Verified** — actual file contents inspected |
| ERP's three-layer noindex protection exists | **Verified** — meta tag and robots.txt confirmed in build output; the `X-Robots-Tag` header is a Render-dashboard feature, so the header itself can only be confirmed once deployed (config is written and YAML-valid, not yet runtime-tested) |
| No sensitive data in the ERP static build | **Verified** — full grep audit of every file in the build output, see `project-status.md` |
| Backend passes all tests under prod-equivalent settings | **Verified for `check --deploy`, `collectstatic`, and `migrate`.** The full authenticated-flow test suite was re-run under prod settings and correctly received HTTPS redirects (expected — `SECURE_SSL_REDIRECT=True` behaving as designed against a test client that doesn't simulate TLS); the suite's actual pass/fail evidence comes from the dev-settings run, which is also what CI uses |
| Render actually deploys this successfully | **NOT RUNTIME VERIFIED** — no Render account exists yet |
| Supabase actually connects and serves data | **NOT RUNTIME VERIFIED** — no Supabase project exists yet |
| Real HTTPS/custom-domain behavior | **NOT RUNTIME VERIFIED** — no domain connected yet |
| GitHub Actions CI runs on a real PR | **NOT RUNTIME VERIFIED** — every step has been manually replayed locally with passing results, but no real Actions run has occurred |
