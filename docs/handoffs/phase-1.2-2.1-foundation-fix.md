PROJECT: Kathwada High School ERP
MODULE: Foundation fix — permission_action_map regression + automatic permission seeding

STATUS:
Fixed, verified, committed. Full backend suite green (52/52), Django
checks clean, no migration drift, ruff clean, frontend build/lint/typecheck
clean.

WHAT WAS BROKEN

Every domain ViewSet built in Phase 1.2 (Classes/Sections/Subjects) and
Phase 2.1 (Student/Enrollment) declared:

    permission_action_map = {...}

but `HasModulePermission.has_permission()` (apps/accounts/permissions.py)
was reading `getattr(view, "action_map", {})` instead — a plain naming
mismatch. Net effect: `resolved_action` was always None for every real
ViewSet, so `HasModulePermission` returned False for every non-superuser,
on every action, across the entire app. Superusers were unaffected (they
short-circuit before this check), which is why the bug wasn't obvious from
a quick manual smoke test as an Admin/superuser account.

This is a *regression*, not a new bug: `permissions.py`'s docstring already
documented, in detail, exactly why the attribute must be named
`permission_action_map` and not `action_map` (DRF's own `ViewSetMixin` sets
an instance attribute literally called `action_map` for an unrelated
purpose — a same-named class attribute gets silently shadowed by it). That
documented warning, and the correct attribute name, were present on
`origin/main` prior to a GitHub Desktop merge that reconciled locally-built
milestone work with the remote history; the merge resolution picked the
wrong side of a divergence in `permissions.py` and reintroduced the exact
bug the docstring was written to prevent. All actual model/view/serializer
code for Milestone 1 and Milestone 2 was correct and unaffected — the fix
here is entirely confined to `permissions.py`.

THE FIX

Restored `permissions.py` to use `permission_action_map` (matching what
every ViewSet already declares) and restored the explanatory docstring/
comments in full. No ViewSet files needed changes — they were already
correct.

SECOND FIX — AUTOMATIC PERMISSION SEEDING

`python manage.py seed_permissions` (the command that inserts the six
`Role` rows, sixteen `Module` rows, and the full default `RolePermission`
matrix from docs/permissions.md) existed but was never invoked
automatically anywhere — not in `backend/build.sh`, not in any deploy
hook. A fresh database (e.g. a new Render deploy) would have zero
`RolePermission` rows, meaning every non-superuser would get a blanket 403
from `HasModulePermission` until someone manually SSHed in and ran the
command — a second, independent way to end up with the exact same
symptom as the bug above, just from missing data instead of missing code.

`seed_permissions` was already written to be fully idempotent (every
insert goes through `get_or_create`), so it's now appended to
`backend/build.sh`, after `migrate`, unconditionally on every deploy.
Verified locally: running it twice in a row creates 0 new rows on the
second run and reports so explicitly. Existing deployments are not at
risk of duplicate rows or data loss — `get_or_create` on already-existing
(role, module, action) tuples is a no-op read.

VERIFICATION PERFORMED

- Backend: 52/52 tests pass (up from 33 failed / 19 passed before the fix).
- `python manage.py check`: 0 issues.
- `python manage.py makemigrations --check --dry-run`: no drift.
- `ruff check .`: all checks passed.
- `seed_permissions` run twice back-to-back: second run creates 0 rows.
- Frontend (`apps/erp`): build, typecheck, and lint all clean.
- Frontend (`apps/public-site`): build and typecheck clean.

WHAT THIS DOES NOT COVER

Row-level scoping (e.g. "Teacher: view own class only", "Parent: view own
children") is still not implemented — it depends on Teacher/Guardian
modules that don't exist yet, and is explicitly called out as a known,
documented gap in `apps/people/views.py`'s docstrings, not something this
fix silently papers over.
