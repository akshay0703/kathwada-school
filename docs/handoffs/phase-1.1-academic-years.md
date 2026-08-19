PROJECT: Kathwada High School ERP
MODULE: Phase 1.1 — Academic Years

STATUS:
Implemented, tested (23/23 backend tests passing, including all 9
pre-existing Phase 0 tests), locally verified end-to-end. Committed.
NOT YET pushed/deployed as of this document being written — see
docs/project-status.md's "Exact next step" for what happens next.

If you are a new Claude picking this up: read docs/project-status.md in
full first — it is the single source of truth and supersedes this file if
they disagree.

WHAT WAS IMPLEMENTED

Backend (backend/apps/academics/):
- models.py — AcademicYear(TimeStampedModel, SoftDeleteModel): school
  (plain CharField, default "Kathwada High School" — see "DEVIATIONS"
  below), label, start_date, end_date, is_current, plus inherited
  created_at/updated_at/deleted_at.
- Three DB-level constraints, all individually verified against a real
  database (not just written and assumed correct):
  1. UniqueConstraint(fields=["school"], condition=Q(is_current=True)) —
     at most one current year per school, enforced by a partial unique
     index, not application discipline.
  2. UniqueConstraint(fields=["school", "label"]) — no duplicate labels.
  3. CheckConstraint(end_date__gt=F("start_date")) — invalid ranges
     rejected at the DB layer, not just the API layer.
- Overlap-between-different-years checking is deliberately NOT a DB
  constraint (no portable Postgres+SQLite range-exclusion mechanism
  without a Postgres-only extension) — enforced in the serializer instead.
- serializers.py — AcademicYearSerializer; is_current is read-only (set
  only via the dedicated mark-current action, never plain create/update).
- views.py — AcademicYearViewSet (ModelViewSet) + a custom mark-current
  action that atomically unsets every sibling's is_current before setting
  the target's, inside one transaction. perform_destroy calls
  instance.soft_delete(), never a real delete — historical data is a hard
  guarantee, not a policy to remember.
- admin.py — registered in Django admin for consistency with other apps.
- migrations/0001_initial.py — generated via makemigrations, applied and
  verified idempotent (migrate run twice, second run "No migrations to
  apply").
- tests/test_academic_years.py — 14 tests covering all 11 requested
  scenarios plus overlap validation and duplicate-label rejection.

Frontend (frontend/):
- packages/api-client/index.ts — added AcademicYear type, PaginatedResponse
  type, ApiError class (carries the real DRF error body so the UI can show
  actual validation messages, e.g. "Date range overlaps with..."), and
  api.academicYears.{list,create,update,remove,markCurrent}.
- apps/erp/app/academic-years/page.tsx — full admin UI: list table, create
  form, inline edit, mark-current button, delete (with confirm), status
  badge for the current year. Role-aware: hides write controls for
  Teacher/Student/Parent, hides Delete specifically for Principal (matching
  the backend's exact permission grant) — this is UI convenience only, not
  security; the real enforcement is 100% server-side.
- apps/erp/app/dashboard/page.tsx — added a link/card to the new module.
- Both frontend apps rebuilt and confirmed: TypeScript clean, ESLint clean,
  static export builds successfully, zero sensitive data in the built
  output (same audit method as Phase 0 — confirmed empty HTML shell).

A REAL BUG FOUND AND FIXED (Phase 0 latent, not introduced by Phase 1.1):
apps/accounts/permissions.py's HasModulePermission used an attribute
literally named `action_map` to hold the custom "DRF action name -> our
permission action" mapping. DRF's own ViewSetMixin ALSO sets an instance
attribute called exactly `action_map` (an HTTP-method -> action-name dict,
assigned by the router in .as_view()), which silently overwrote our
class-level attribute at request time. This meant EVERY real DRF ViewSet
using HasModulePermission would incorrectly deny all permission checks —
but this was invisible in Phase 0 because Phase 0's only permission test
used a plain APIView (AdminOnlyStubView), which never exercises the
action_map code path at all. AcademicYearViewSet is the first real
ViewSet in the project, and its first test run surfaced this immediately.

Fixed by renaming our custom attribute to `permission_action_map`
everywhere (apps/accounts/permissions.py, apps/academics/views.py,
docs/permissions.md, docs/api-spec.md). Root-caused via direct debugging —
isolated a minimal reproduction, then confirmed via
`inspect.getsource(ViewSetMixin.initialize_request)` that DRF really does
set that exact attribute name. Full test suite re-run and passing after
the fix (23/23).

THIS MATTERS FOR THE FUTURE: any future domain app's ViewSet must use
`permission_action_map`, never `action_map`, when declaring its permission
mapping for HasModulePermission. This is now documented in the permission
class's own docstring, not just here.

API ENDPOINTS (all under /api/v1/):
- GET    /academic-years/              — list (paginated)
- POST   /academic-years/              — create
- GET    /academic-years/{id}/         — retrieve
- PATCH  /academic-years/{id}/         — partial update
- DELETE /academic-years/{id}/         — soft delete
- POST   /academic-years/{id}/mark-current/ — atomically mark as the
  current year, unsetting any previous current year for the same school

PERMISSIONS (seeded via apps/accounts/management/commands/seed_permissions.py):
Admin: View/Create/Edit/Delete/Export (full)
Principal: View/Create/Edit/Export (no Delete)
Teacher/Student/Parent: View only
Anonymous: denied entirely

DEVIATIONS FROM THE LITERAL PHASE 1.1 SPEC (both explicit, neither silent —
see docs/project-status.md's "Phase 1.1 status" section for the full
reasoning, this is the short version):
1. Principal was NOT granted Delete (spec said Admin/Principal for
   create/update/delete) — matches the pattern used for nearly every other
   module in the approved matrix, and Academic Years are foundational data.
2. "school" field is a plain CharField default, not a foreign key to a
   School model — no School entity exists anywhere in the approved schema
   (this is a single-school system by design); adding one would have been
   an unapproved schema expansion.

TESTS: 23/23 passing (14 new Phase 1.1 + 9 pre-existing Phase 0, all
re-verified together). ruff clean. makemigrations --check clean.
Migrations idempotent (verified twice). Django system check clean.

DEPLOYMENT: Code is committed locally. NOT yet pushed to GitHub as of this
document. Once pushed, the already-proven CI-gated pipeline (see
docs/project-status.md's "Automated deployment pipeline status", proven in
run #5) handles the rest automatically — no manual Render steps needed.

KNOWN LIMITATIONS:
- No frontend automated tests exist yet (build/lint/TypeScript checks are
  the current frontend quality gate, consistent with Phase 0 — no test
  framework like Jest/Playwright has been introduced, and none was
  requested for Phase 1.1 specifically beyond "frontend builds
  successfully," which is verified).
- AcademicYear has no downstream references yet (no ClassSection, Exam,
  etc. point to it) — those arrive in later Phase 1.x increments per
  docs/database-schema.md.
- The `school` field's real long-term meaning (single hardcoded value vs.
  eventually becoming a real FK) is an open question if the project ever
  needs true multi-school support — not needed now, flagged for awareness.

EXACT NEXT TASK:
1. Push this commit to GitHub (user does this via GitHub Desktop).
2. Let the automated pipeline deploy it (no manual Render steps).
3. User opens the live ERP, logs in as Admin, and verifies the Academic
   Years module works against the real live database.
4. Report that live verification back, then Phase 1.2 can be discussed and
   approved separately — per the user's explicit "one small module → test
   → CI → deploy → live verification → approval → next module" workflow.

Do NOT start Phase 1.2 (Classes/Sections/Subjects, or anything else) until
that live verification and explicit approval happens.
