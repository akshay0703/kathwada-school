# 0001 — Permissions as data, not code

Date: Phase 0
Status: Accepted

## Context

The prototype had no role concept at all — two hardcoded, identical,
client-side-only credentials (see `prototype-analysis.md` §14). You approved
a six-role matrix (`permissions.md`) as a "starting point" and explicitly
asked for a system that's "adjustable later without rewriting the
application."

## Decision

Model `Role`, `Module`, and `RolePermission` as database tables. A single
generic DRF permission class (`HasModulePermission`) checks
`(request.user.role, view.module_key, resolved_action)` against the
`RolePermission` table. Every domain viewset declares its `module_key` and
action mapping; none implement bespoke permission logic.

## Consequences

- Adjusting who can do what is a data edit (add/remove a row, e.g. via
  Django admin), not a code change or redeploy.
- New modules require one new `Module` row plus the relevant viewset
  declaring `module_key` — no new permission-checking code.
- Row-level scoping (e.g. "Teacher sees only their assigned classes") is
  still enforced by queryset filtering in each domain app, not by this
  table — the table only answers "can this role do this action on this
  module at all." This is documented explicitly in `permissions.md` so it
  isn't mistaken for a limitation of the design.
