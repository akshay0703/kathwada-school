# 0004 — CI-gated deploys via Render Deploy Hooks

Date: Post-Phase-0 deployment automation
Status: Accepted

## Context

Render's native GitHub integration auto-deploys on every push by default —
this was already happening and caused real confusion during manual
deployment (a stray click on "Rollback" briefly undid a fix because two
deploys were racing). More importantly, it deploys regardless of whether
tests/lint/build actually pass — there was no gate at all. The requirement
was: push to main → CI validates → only then does production deploy,
automatically, with no manual Render interaction for routine changes.

Two realistic options existed:
1. **Render Deploy Hooks** (a per-service secret URL that triggers a deploy
   when POSTed to) triggered from a GitHub Actions job that only runs after
   other jobs succeed (`needs:`).
2. **Render API + API key**, giving GitHub Actions full programmatic control
   (trigger deploys, poll status, etc.), requiring a Render API key stored as
   a GitHub secret.

## Decision

Use Deploy Hooks (option 1). Turn off Render's native auto-deploy
(`autoDeploy: false` in `render.yaml`, one per service) so Deploy Hooks
become the *only* deploy trigger. Add a `deploy` job in CI with
`needs: [backend, frontend, migration-script]` so it cannot run unless every
other check passed. Follow it with a `smoke-test` job that polls the live
URLs with retries (since Deploy Hooks fire-and-forget — the POST returns
immediately, the actual deploy takes a minute or two).

Deliberately did **not** add a Render API key. Polling the live public URLs
directly (health endpoint, auth endpoint, both frontends, sitemap/robots)
achieves the same real-world confirmation ("is the deployed thing actually
working") without a second class of secret, one fewer GitHub secret to
manage, and no dependency on Render's API shape.

## Consequences

- Ongoing feature development requires zero manual Render interaction — the
  explicit target workflow requested.
- A failing test, lint error, or uncommitted migration file structurally
  cannot reach production — there is no code path where `deploy` runs
  without `backend`/`frontend`/`migration-script` having already succeeded.
- No automatic rollback exists, on purpose — see `deployment.md`'s
  explanation of why (a reverted deploy can't safely un-apply an already-run
  migration). A failed `smoke-test` is a loud, visible signal, not an
  automatic action.
- One-time manual setup cost: create 3 Deploy Hook URLs in Render (dashboard
  clicks) and add them as 3 GitHub Actions secrets (dashboard clicks) — see
  `deployment.md`'s "One-time setup" walkthrough. This has not yet been
  completed as of this ADR being written — see `project-status.md`.
- The `smoke-test` job's retry-loop approach (fixed polling against public
  URLs) is simpler but less precise than polling Render's own deploy-status
  API would be. If this ever proves unreliable in practice (e.g. false
  failures from cold starts exceeding the retry window), revisit toward
  option 2 rather than lengthening the polling window indefinitely.
