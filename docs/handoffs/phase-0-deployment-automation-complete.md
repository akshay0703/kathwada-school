PROJECT: Kathwada High School ERP

CURRENT PHASE:
Phase 0 complete AND deployed to real, live infrastructure (Render +
Supabase). CI-gated automated deployment pipeline built on top of it.
Phase 1 (first real domain features) not started — awaiting approval.

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

AUTOMATED DEPLOYMENT PIPELINE (built this session, NOT yet proven end-to-end):
- .github/workflows/ci.yml now has a `deploy` job (needs: backend, frontend,
  migration-script all passing) that POSTs to 3 Render Deploy Hook URLs
  (stored as GitHub secrets RENDER_DEPLOY_HOOK_BACKEND,
  RENDER_DEPLOY_HOOK_PUBLIC_SITE, RENDER_DEPLOY_HOOK_ERP), followed by a
  `smoke-test` job that polls the live URLs with retries.
- render.yaml now sets autoDeploy: false on all three services — Render no
  longer deploys independently on every push; only the CI-triggered Deploy
  Hooks can trigger a deploy now.
- Also added: `makemigrations --check --dry-run` as a CI guard step, so an
  uncommitted model change fails the build rather than silently drifting.
- ONE-TIME MANUAL STEP NOT YET DONE: creating the 3 Deploy Hook URLs in
  Render and adding them as the 3 GitHub secrets above (6 dashboard clicks,
  see docs/deployment.md's "One-time setup" section for exact steps). Until
  this is done, pushes to main will NOT auto-deploy (Render's own
  auto-deploy is off, and nothing has replaced it yet for the user).

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
- smoke-test job's curl logic (syntactically verified against real URLs,
  but this sandbox's network egress blocks onrender.com — confirmed via
  x-deny-reason header, not assumed; will prove itself on the first real run)
- autoDeploy: false actually stopping Render's independent deploys
- The full CI-gated pipeline firing end-to-end for a real code change

KNOWN LIMITATIONS (still true, unchanged):
- Free tier: backend sleeps after 15 min idle (~30-60s cold start)
- Free tier: Supabase may pause after 7 days with zero database activity —
  do NOT build a keep-alive workaround, this is documented/accepted behavior
  per explicit user decision
- No automatic rollback — deliberate, see docs/decisions/0004

NEXT ACTION:
User needs to complete the one-time Deploy Hook + GitHub Secrets setup
(docs/deployment.md, "One-time setup" section, 6 dashboard clicks). Offer to
walk them through it in the same beginner-friendly WHAT TO DO format used
throughout this project, one step at a time, waiting for confirmation after
each click — that pattern worked well and should continue.

AFTER THAT:
The next push to main (any future feature work) will be the first real
end-to-end test of the automated pipeline. Once confirmed working, update
project-status.md's "Automated deployment pipeline status" table from
CODE-COMPLETE to VERIFIED for each item, then Phase 1 can begin on the
user's explicit go-ahead. Phase 1 scope is the domain apps listed under
"NOT COMPLETE" in project-status.md's Phase 0 table, built against
docs/database-schema.md and docs/permissions.md exactly as documented.
