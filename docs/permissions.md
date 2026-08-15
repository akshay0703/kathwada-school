# Roles & Permissions

**Status:** Approved matrix (starting point, adjustable). Enforcement
mechanism **implemented and verified** in Phase 0 (`apps/accounts` — see
`project-status.md` for test evidence).

## Approved roles (fixed set, six roles)

Admin · Principal · Teacher · Staff · Student · Parent

Stored as `Role` rows (`apps/accounts/models.py`), not a Python enum — new
roles can be added later as a data change.

## Enforcement architecture — the important part

**All permissions are enforced server-side, always.** The frontend never
decides what a user can do; it only reflects what the API allows, and the API
re-checks on every request regardless of what the UI shows.

The mechanism (already built, not proposed):

- `Module` — a registry of ERP modules (Students, Marks, Attendance, ...),
  one row per line of the matrix below.
- `RolePermission` — one row = "this Role may perform this Action on this
  Module." This **is** the permission matrix, stored as data.
- `HasModulePermission` — a single generic DRF permission class every
  viewset/view reuses. It denies by default; a view must explicitly declare
  its `module_key` and either an `action_map` (for ViewSets) or
  `required_action` (for plain APIViews).
- `python manage.py seed_permissions` — seeds the six roles, the module
  registry, and the full default matrix below as data.

**Why this matters for "adjustable later without rewriting the application":**
changing what a Teacher can do to the Fees module is an admin data edit
(add/remove a `RolePermission` row), never a code change or redeploy. This was
built specifically because you approved the matrix below only as a *starting
point*.

## Default permission matrix

Legend: **V**=View **C**=Create **E**=Edit **D**=Delete **P**=Publish
**X**=Export · `—` = no access

| Module | Admin | Principal | Teacher | Staff | Student | Parent |
|---|---|---|---|---|---|---|
| Students | VCEDX | VCEX | V (own class only) | VCEX | V (own record) | V (own children) |
| Guardians | VCEDX | VEX | V | VCEX | — | V (own record), E (own contact info) |
| Teachers | VCEDX | VEX | V (own record), E (own contact info) | V | — | — |
| Classes / Sections | VCEDX | VCEX | V (assigned only) | VX | V (own class) | V (own child's class) |
| Subjects | VCEDX | VEX | V | V | V | V |
| Academic Years | VCEDX | VX | V | V | V | V |
| Exams & Exam Components | VCEDX | VCEX | V | V | V (own results) | V (own child's results) |
| Marks Entry | VCEDX | VEX (override/moderation) | VCE (assigned subjects/classes only) | — | V (own, once published) | V (own child's, once published) |
| Attendance | VCEDX | VEX | VCE (own classes only) | VC | V (own) | V (own child's) |
| Fees | VCEDX | VX | — | VCEX | V (own) | V (own child's), X (own receipts) |
| Library | VCEDX | VX | V, C (issue/return) | VCEDX | V (own issues) | V (own child's issues) |
| Documents | VCEDX | VX | VC (own uploads) | VC | V (own) | V (own child's) |
| Report Cards | VCEDPX | VEPX (approve/publish) | VC (draft, assigned classes) | VX | V (own, once published) | V (own child's, once published), X |
| Audit Logs | VX | VX | — | — | — | — |
| Users & Role Management | VCEDX | — | — | — | — | — |
| Public Website Content (CMS) | VCEDPX | VEP | — | — | — | — |

This exact matrix is seeded as data by `manage.py seed_permissions`
(`apps/accounts/management/commands/seed_permissions.py`) — that file is the
executable source of truth; this table is the human-readable mirror of it.

## Scoping rules not expressible in a flat V/C/E/D/P/X table

The matrix above answers "can this role do this action on this module at
all" — not "on which specific rows." These scoping rules are enforced by
queryset filtering in each Phase 1+ domain app, not by the `RolePermission`
table itself:

- **Teacher → only assigned classes/subjects.** Enforced via the
  `TeacherAssignment` table (`database-schema.md`): a Teacher's queryset for
  Students/Marks/Attendance is filtered to `ClassSection`s and `Subject`s
  they're actually assigned to.
- **Student → own published records only.** A Student's queryset for
  Marks/Report Cards is filtered to their own `student_id` **and** to
  records where `ReportCard.status == published` (or equivalent) — draft
  marks a Teacher is still entering are never visible to the Student.
- **Parent → own child's published records only.** Same as Student, filtered
  via `StudentGuardian` to the children linked to that Parent's account.
- **Principal/Admin → approval/publishing authority.** Only these two roles
  hold the `publish` action on `Marks Entry`/`Report Cards` in the matrix
  above — a Teacher can create/edit a draft report card but the `Publish`
  action is not in their row, so the API will reject the call even if a
  compromised frontend tried to send it.

## Draft → publish workflow (approved)

1. Teacher enters/edits marks for their assigned classes/subjects → draft
   report card auto-generated or manually triggered.
2. Principal/Admin reviews and publishes.
3. Only after publish do Student/Parent gain View access to that report card
   and its underlying marks.

This is why "Marks Entry" and "Report Cards" are the only two modules with a
`Publish` (`P`) action in the matrix, and why Student/Parent's `V` on those
rows is explicitly annotated "once published."
