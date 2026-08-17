PROJECT: Kathwada High School ERP

CURRENT PHASE:
Phase 0 complete, deployed to real live infrastructure, AND the automated
CI-gated deployment pipeline is fully set up and PROVEN working end-to-end
(GitHub Actions run #5: all 6 jobs green, deploy + smoke-test both
succeeded for real). Phase 1 (first real domain features) not started —
awaiting approval.

If you are a new Claude picking this project up: read docs/project-status.md
in full before doing anything else. It is the single source of truth and
supersedes this file and any summary below if they disagree.

DO NOT:
- Rewrite architecture
- Replace Django, PostgreSQL, Next.js, Render, or Supabase
- Change grading rules
- Start Phase 1 without approval
- Re-run the Render/Supabase account setup — it's done, see below
- Reintroduce a keep-alive cron for Supabase (explicitly rejected earlier)
- Add automatic rollback (explicitly rejected — unsafe with migrations)
- Ask the user to use Docker, Linux, SSH, or a terminal — they are a
  deliberate beginner-mode user; every interaction so far has been dashboard
  clicks only, and future interactions should be too

LIVE, REAL INFRASTRUCTURE (already set up, do not repeat):
- Render account connected to GitHub repo akshay0703/kathwada-school
- Three Render services live: kathwada-public-site (static),
  kathwada-erp (static), kathwada-erp-backend (Python web service, free tier)
- Supabase project "kathwada-erp" (Mumbai region) — real Postgres database,
  Storage bucket "kathwada-documents" with S3-compatible access configured
- First Admin account created and confirmed working (login tested live)
- All URLs:
  - https://kathwada-public-site.onrender.com
  - https://kathwada-erp.onrender.com
  - https://kathwada-erp-backend.onrender.com

REAL BUGS FOUND AND FIXED DURING LIVE DEPLOYMENT (all now fixed in code):
1. Supabase connection string contained a literal "[YOUR-PASSWORD]"
   placeholder that wasn't substituted — user error, not a code bug, but
   worth knowing the failure mode (django.db.utils.OperationalError:
   password authentication failed) if it ever recurs.
2. Render's free Web Service plan has no Shell/SSH access, so the standard
   `createsuperuser` interactive command couldn't be used. Fixed by adding
   apps/accounts/management/commands/create_admin_from_env.py — idempotent,
   reads DJANGO_SUPERUSER_EMAIL/PASSWORD env vars, safe to run on every
   deploy, never resets an existing password.
3. Cross-site session cookie: Render isolates each service's subdomain as a
   genuinely separate "site" even though they share the onrender.com parent
   domain. Default SESSION_COOKIE_SAMESITE="Lax" silently dropped the
   session cookie after login. Fixed in backend/config/settings/prod.py:
   SESSION_COOKIE_SAMESITE = "None" and CSRF_COOKIE_SAMESITE = "None"
   (both require Secure=True, already set). This fix remains correct even
   after a future custom domain puts both apps under one shared parent.

AUTOMATED DEPLOYMENT PIPELINE (built and PROVEN this session, run #5):
- .github/workflows/ci.yml has a `deploy` job (needs: backend, frontend,
  migration-script all passing) that POSTs to 3 Render Deploy Hook URLs
  (stored as GitHub secrets RENDER_DEPLOY_HOOK_BACKEND,
  RENDER_DEPLOY_HOOK_PUBLIC_SITE, RENDER_DEPLOY_HOOK_ERP), followed by a
  `smoke-test` job that polls the live URLs with retries.
- render.yaml sets autoDeploy: false on all three services — confirmed
  working: the only deploy trigger in run #5 was CI, not Render itself.
- `makemigrations --check --dry-run` runs as a CI guard step, so an
  uncommitted model change fails the build rather than silently drifting.
- Deploy Hook URLs created in Render + added as the 3 GitHub secrets —
  DONE, confirmed working.
- BONUS: the first real `docker-build` run (never previously executed with
  an actual Docker daemon) caught a real bug — a doubled `apps/apps/...`
  path in docker/frontend.Dockerfile, silently wrong since Phase 0. Fixed
  in commit 994773d. Exactly the kind of thing this pipeline exists to catch.

VERIFIED (this session, evidence in docs/project-status.md):
- Live deployment: backend, database connection, public site, ERP, sitemap,
  robots.txt, login, session persistence, role-based response — all
  personally confirmed working by the user on real infrastructure.
- CI backend job re-simulated locally in exact order after all changes:
  ruff, migrate, makemigrations --check, pytest (9/9), Django check — all
  passed.
- render.yaml and ci.yml both YAML-valid, `needs:` dependency chains
  confirmed correct.

CODE-COMPLETE, NOT RUNTIME VERIFIED:
- (nothing remaining in this category as of run #5 — everything that was
  here previously is now VERIFIED, see above)

KNOWN LIMITATIONS (still true, unchanged):
- Free tier: backend sleeps after 15 min idle (~30-60s cold start)
- Free tier: Supabase may pause after 7 days with zero database activity —
  do NOT build a keep-alive workaround, this is documented/accepted behavior
  per explicit user decision
- No automatic rollback — deliberate, see docs/decisions/0004

NEXT ACTION:
None required for the pipeline itself — it's proven and working. The next
natural step is Phase 1 (first real domain feature), on the user's explicit
go-ahead. Phase 1 scope is the domain apps listed under "NOT COMPLETE" in
project-status.md's Phase 0 table, built against docs/database-schema.md
and docs/permissions.md exactly as documented. When Phase 1 starts, the
normal workflow becomes: user asks for a feature → Claude builds, tests,
commits, pushes → CI validates → auto-deploys → user tests it live. No
Render/GitHub Actions/Supabase manual steps should be needed for routine
feature work from this point forward.
