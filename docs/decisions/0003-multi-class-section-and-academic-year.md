# 0003 — Multiple simultaneous class-sections and first-class Academic Year

Date: Phase 0
Status: Accepted

## Context

The prototype only ever supports one class-section at a time
(`state.classLabel` is a single free-text string). You confirmed production
must support many simultaneous class-sections (Std 8-A, 8-B, 9-A, 9-B, 10-A,
10-B, ...) and that Academic Year must be first-class, with historical data
never overwritten on promotion.

## Decision

- `Class` and `Section` are separate entities; `ClassSection` is the actual
  per-year offering (`class_id, section_id, academic_year_id,
  class_teacher_id`).
- `AcademicYear` is a standalone entity, not a string field.
- `Enrollment` (`student_id, class_section_id, roll_no, status`) is the join
  between a student and a specific year's class-section. Promoting a student
  creates a new `Enrollment` row; it never mutates a previous year's row.
- Roll number uniqueness is a database constraint scoped to
  `class_section_id`, fixing a data-integrity gap the prototype had (no
  uniqueness enforcement at all).

## Consequences

- Every year-scoped fact (`Mark`, `AttendanceRecord`, `FeeInvoice`,
  `ReportCard`) is reachable through `Enrollment`/`ClassSection`, so a
  student's full multi-year history stays queryable without ambiguity about
  which year a given row belongs to.
- Teachers are assigned per `ClassSection` + `Subject` (`TeacherAssignment`),
  which is what makes per-teacher scoped permissions (`permissions.md`)
  possible in the first place.
