# Emergency Operations

**You should almost never need this document.** Normal development (Claude
builds a feature → tests → pushes → CI → auto-deploy → you test it live) does
not require any of the steps below. This page exists only for rare
situations — something breaks, you need to check on something manually, or
CI/deploy needs a nudge.

Every procedure below is dashboard clicks only — no terminal, no Docker, no
SSH, no database CLI, matching how the rest of this project's deployment was
set up.

---

## "The live site looks broken — what do I check first?"

1. **Open:** [dashboard.render.com](https://dashboard.render.com)
2. **Click:** into `kathwada-erp-backend`
3. **Look at:** the colored dot next to the service name — green means running, red/gray means it crashed or is asleep (see "cold start" note below)
4. **Click:** "Logs" in the sidebar, switch the dropdown to **"All logs"**, and read the most recent lines — most errors are self-explanatory (e.g., "password authentication failed" means a credential is wrong)

**Also check:** [github.com/akshay0703/kathwada-school/actions](https://github.com/akshay0703/kathwada-school/actions) — if the most recent run shows a red ✕, that tells you exactly which check failed (lint, tests, build, or the post-deploy smoke test) and deployment was correctly blocked.

## "It's just slow / not responding"

This is very likely the free tier's normal cold-start behavior, not a bug: **the backend goes to sleep after 15 minutes with no traffic, and takes 30-60 seconds to wake up on the next request.** Just wait a minute and reload. See `deployment.md`'s Stage A/B table for when this stops being acceptable (Stage B, once real student data exists).

## "I need to redeploy without any code change" (e.g., to pick up a new environment variable)

**WHAT TO DO**
1. Open: `dashboard.render.com`, click into the service (`kathwada-erp-backend`, `kathwada-public-site`, or `kathwada-erp`)
2. Click: **"Manual Deploy"** (top-right)
3. Select: **"Deploy latest commit"**
4. Do NOT change: anything else
5. Expected result: a new deploy starts, using the same code already on GitHub

## "I need to restart the backend" (it's stuck, not crashed)

**WHAT TO DO**
1. Open: `kathwada-erp-backend` service page
2. Click: the **"Manual Deploy"** dropdown → **"Restart service"** (if shown), or use "Deploy latest commit" as above — either restarts the process
3. Expected result: a brief downtime (seconds), then the service comes back up

## "I need to undo a bad deploy" (roll back)

**WHAT TO DO**
1. Open: the service page → **"Events"** in the sidebar
2. Find: the last known-good deploy in the list (one that showed "Live" and worked)
3. Click: the **"Rollback"** button next to that specific entry
4. **Important caution:** if the bad deploy included a database migration, rolling back the *code* does not undo the migration — the database stays on the newer schema. This is exactly why automatic rollback isn't built into the pipeline (see `deployment.md`). If you're unsure whether a migration was involved, stop and ask Claude before rolling back, rather than guessing.

## "I need to check logs for a specific time"

**WHAT TO DO**
1. Open: the service page → **"Logs"**
2. Click: the **"All logs"** dropdown (not just "Application logs" — that view only shows runtime output, not the build/migration output)
3. Click: the date/time range selector (e.g., "Last hour") and adjust if needed
4. Use: the search box to filter by a keyword (e.g., `superuser`, `error`, `migrate`)

## "I need to run a migration manually" (should almost never be needed — migrations already run automatically on every deploy)

This should not come up in normal use — `build.sh` runs `python manage.py migrate` automatically on every deploy, and a failed migration already blocks that deploy from going live (see `deployment.md`). If you genuinely need to run one out-of-band: tell Claude, and a new deploy will be the mechanism (Render's free tier has no Shell access — see the note in `deployment.md` about why `create_admin_from_env` exists in the first place).

## "I need to create or reset an Admin account"

**Creating the first Admin** is already automatic (see `deployment.md`'s "Admin account" section) — it happens once, safely, via the `DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD` environment variables already set in Render.

**Creating additional Admin/Principal/Teacher/etc. accounts** should be done from inside the ERP itself once Phase 1's user-management screens exist — not via environment variables or scripts. That's the intended long-term path (see `permissions.md`).

**If you're genuinely locked out** (forgot the Admin password, no other Admin exists):

**WHAT TO DO**
1. Open: Render dashboard → `kathwada-erp-backend` → **"Environment"** → **"Edit"**
2. Enter: update `DJANGO_SUPERUSER_PASSWORD` to a new password (save it privately), and add a **new** row: **Key** `DJANGO_SUPERUSER_RESET_PASSWORD` → **Value** `true`
3. Click: **"Save Changes"** — this triggers a redeploy
4. Wait: for the deploy to finish, then log in with the new password
5. **Immediately after confirming login works:** go back to Environment → Edit → **delete** the `DJANGO_SUPERUSER_RESET_PASSWORD` row entirely, and Save Changes again
6. Do NOT change: leave `DJANGO_SUPERUSER_RESET_PASSWORD` set after you're done — every future deploy would silently reset the password back to this same value again, including overwriting any password change made later through the ERP itself

This two-variable design (a separate opt-in flag, not just editing the password) is deliberate — see `apps/accounts/management/commands/create_admin_from_env.py`'s docstring for why.

## "I need to verify the database is actually reachable"

**WHAT TO DO**
1. Open a browser tab, go to: `https://kathwada-erp-backend.onrender.com/api/v1/health/`
2. Expected result: `{"status":"ok","database":true}`
3. If it says `"database":false` or the page doesn't load at all: check Supabase's own dashboard (is the project paused? See `deployment.md`'s note on free-tier pausing) before assuming the backend itself is broken.

## "I need to check whether the automated deploy actually finished"

**WHAT TO DO**
1. Open: [github.com/akshay0703/kathwada-school/actions](https://github.com/akshay0703/kathwada-school/actions)
2. Click: the most recent workflow run
3. Look at: the job list — `deploy` (green check) means the Render deploy was triggered; `smoke-test` (green check) means the live site was actually verified working afterward. If `smoke-test` is red, the deploy happened but something isn't responding correctly — check Render's logs next.

---

## What you should NOT need to do routinely

If you find yourself doing any of the following more than once in a rare while, something about the pipeline itself needs fixing — tell Claude rather than treating it as a normal chore:
- Manually clicking "Deploy" after a normal code change (should be automatic via CI)
- Manually running migrations (should be automatic via `build.sh`)
- Manually creating environment variables for a new feature (Claude should tell you exactly what to add, once, when a feature genuinely needs a new one)
- Manually checking whether a deploy succeeded (the `smoke-test` CI job already tells you)
