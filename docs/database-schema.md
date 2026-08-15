# Database Schema — Approved ERD

**Status:** Approved design. **Not yet implemented** — no migrations exist
for any of these entities yet (Phase 0 only implements `User`, `Role`,
`Module`, `RolePermission`, `AuditLog`; see `project-status.md`). This is the
target schema for Phase 1 onward.

## Diagram

```mermaid
erDiagram
    USER ||--o| STUDENT : "1:0..1 login"
    USER ||--o| TEACHER : "1:0..1 login"
    USER ||--o| GUARDIAN : "1:0..1 login"
    USER ||--o| STAFF_PROFILE : "1:0..1 login"
    USER }o--|| ROLE : "has"

    ACADEMIC_YEAR ||--o{ CLASS_SECTION : "offered in"
    CLASS ||--o{ CLASS_SECTION : "has sections"
    CLASS_SECTION ||--o{ ENROLLMENT : "contains"
    STUDENT ||--o{ ENROLLMENT : "enrolled via"
    CLASS_SECTION }o--o{ SUBJECT : "offers (via CLASS_SECTION_SUBJECT)"
    TEACHER }o--o{ CLASS_SECTION_SUBJECT : "assigned to (via TEACHER_ASSIGNMENT)"

    STUDENT ||--o{ STUDENT_GUARDIAN : "has"
    GUARDIAN ||--o{ STUDENT_GUARDIAN : "guardian of"

    ACADEMIC_YEAR ||--o{ EXAM : "scheduled in"
    EXAM ||--o{ EXAM_COMPONENT : "made of"
    EXAM_COMPONENT ||--o{ EXAM_COMPONENT_SUBJECT_CONFIG : "max/pass per subject"
    SUBJECT ||--o{ EXAM_COMPONENT_SUBJECT_CONFIG : "configured for"

    STUDENT ||--o{ MARK : "scores"
    EXAM_COMPONENT ||--o{ MARK : "recorded for"
    SUBJECT ||--o{ MARK : "in subject"
    MARK }o--|| USER : "entered_by"

    STUDENT ||--o{ REPORT_CARD : "has"
    EXAM ||--o{ REPORT_CARD : "generated for"
    REPORT_CARD ||--o{ REPORT_CARD_SUBJECT_RESULT : "breakdown"
    REPORT_CARD ||--o| DOCUMENT : "pdf export"

    STUDENT ||--o{ ATTENDANCE_RECORD : "has"
    CLASS_SECTION ||--o{ ATTENDANCE_RECORD : "context"
    USER ||--o{ ATTENDANCE_RECORD : "marked_by"

    CLASS_SECTION ||--o{ FEE_STRUCTURE : "defines"
    STUDENT ||--o{ FEE_INVOICE : "billed"
    FEE_STRUCTURE ||--o{ FEE_INVOICE : "generates"
    FEE_INVOICE ||--o{ FEE_PAYMENT : "paid via"

    BOOK ||--o{ BOOK_COPY : "has copies"
    BOOK_COPY ||--o{ BOOK_ISSUE : "issued as"
    STUDENT ||--o{ BOOK_ISSUE : "borrows"

    STUDENT ||--o{ DOCUMENT : "owns"
    TEACHER ||--o{ DOCUMENT : "owns"

    USER ||--o{ AUDIT_LOG : "acted as"
```

## Entities requiring special attention

### Academic Year — first-class, never overwritten

`AcademicYear` (`id, label, start_date, end_date, is_current`) is a real,
standalone entity, not a free-text field on another table (the prototype's
`state.year` was a single string — see `prototype-analysis.md` §3). Every
year-scoped fact — `ClassSection`, `Enrollment`, `Exam`, and (transitively)
`Mark`/`AttendanceRecord`/`FeeInvoice` — carries its own `academic_year_id`.
**A student's promotion to a new year creates a new `Enrollment` row; it does
not modify or delete the previous year's `Enrollment`, `Mark`, `Attendance`,
`FeeInvoice`, or `ReportCard` rows.** A student in Std 10-A in 2026–27 who was
in Std 9-A in 2025–26 has two `Enrollment` rows, and both years' full academic
history remains independently queryable.

### Class / Section / ClassSection / Enrollment

- `Class` — e.g. "Std 10". `Section` — e.g. "A". Modeled separately so a
  Section name could theoretically be reused across classes.
- `ClassSection` — the actual per-year offering: `(class_id, section_id,
  academic_year_id, class_teacher_id)`. This is what "Std 10-A in 2026–27"
  actually refers to.
- `Enrollment` — `(student_id, class_section_id, roll_no, status)`. Roll
  number uniqueness is enforced by a **database constraint scoped to
  `class_section_id`** — this directly fixes a data-integrity gap in the
  prototype (see `prototype-analysis.md` §2/§17), where roll numbers were
  freely editable text with no uniqueness check at all.
- This design is what makes "multiple simultaneous class-sections" (Std 8-A,
  8-B, 9-A, 9-B, 10-A, 10-B, ...) possible under one system, which the
  prototype could not do.

### Guardian / StudentGuardian

`Guardian` is a standalone entity (not a flat string field on `Student`, as
in the prototype). `StudentGuardian` is a join table with an
`is_primary_contact` flag, supporting **multiple guardians per student** —
another prototype gap this fixes.

### Exam / ExamComponent / ExamComponentSubjectConfig

Replaces the prototype's hardcoded five-test array plus one virtual Internal
component (see `grading-engine.md` for the business logic these carry).
`Exam` and `ExamComponent` are database rows, editable via admin, not
hardcoded in application code. `ExamComponentSubjectConfig` allows per-subject
max/pass overrides (an improvement over the prototype's single uniform
max/pass applied identically to every subject) — but a uniform default can
still reproduce the prototype's exact current behavior.

### Mark / ReportCard / ReportCardSubjectResult

`Mark` is one row per `(student, exam_component, subject)`. `ReportCard` is a
cached/materialized rollup per `(student, exam)` — computed by the grading
engine (see `grading-engine.md`), persisted rather than recomputed client-side
on every render as the prototype did. `ReportCardSubjectResult` holds the
per-subject breakdown backing the printed report card layout.

### User vs. domain profile tables

`User` (email, password_hash, role) is the auth table only. `Student`,
`Teacher`, `Guardian`, and staff each have their own profile table with a
**nullable** 1:0..1 link to `User` — not every Student necessarily has login
access on day one. This was an explicit assumption flagged during the
original analysis and confirmed as correct.

### AuditLog

Already implemented in Phase 0 (`apps/audit/models.py`) at the request level
(who called which endpoint, when, what status came back). Phase 1+ domain
apps additionally write entity-level rows with `before_json`/`after_json`
diffs on Create/Update/Delete/Publish/Export — the schema already supports
this without changes.

## Full field-level detail

See `prototype-analysis.md` §3.2 for the complete column-by-column listing of
every entity above (this file intentionally keeps to relationships and the
handful of entities needing extra explanation, per the instruction not to
duplicate large amounts of content).
