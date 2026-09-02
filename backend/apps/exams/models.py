from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel


class Exam(TimeStampedModel, SoftDeleteModel):
    """
    An exam scheduled within an academic year — see docs/database-schema.md's
    ERD (`ACADEMIC_YEAR ||--o{ EXAM`) and docs/prototype-analysis.md §17.2's
    field list: "Exam — id, academic_year_id, code (e.g. FST/SST/UT1/UT2/
    MAIN/INTERNAL), name, sequence_order."

    Deliberately simplified from the full approved schema for this MVP
    batch (per instruction: "do not build overly complex grading logic
    unless existing project docs require it" / "focus on a reliable
    working MVP" / "do not start Report Cards yet"):

    - No `ExamComponent` layer. The approved ERD splits an Exam into one or
      more ExamComponents (e.g. Internal Marks' 3 sub-parts: P1/P2/P3) with
      per-subject max/pass configured via a further
      `ExamComponentSubjectConfig` table. That two-table indirection exists
      specifically to support the prototype's multi-part Internal Marks
      exam type — a report-card-adjacent feature explicitly out of scope
      here. This MVP instead lets `ExamSubject` (below) carry `max_marks`
      directly per (exam, class_section, subject), which is exactly
      equivalent for any *simple* exam (FST, SST, UT1, UT2, Main) — the
      overwhelming majority of exam types — and is upgradeable to the full
      ExamComponent model later without touching this table's meaning.
    - No `ReportCard`, no grading/ranking/pass-fail computation, no
      draft->publish workflow. Checked against the actual seed data this
      codebase runs on (apps/accounts/management/commands/seed_permissions.py):
      the "marks" and "exams" module rows there do NOT include the PUBLISH
      action at all (only "report_cards" and "website_cms" do) — so
      Student/Parent's View permission on Marks is unconditional once
      scoped to their own record, no publish gate to build for this batch.
    """

    academic_year = models.ForeignKey("academics.AcademicYear", on_delete=models.PROTECT, related_name="exams")
    code = models.CharField(max_length=20, help_text="Short code, e.g. 'UT1', 'FST', 'MAIN'")
    name = models.CharField(max_length=100, help_text="e.g. 'Unit Test 1'")
    start_date = models.DateField()
    end_date = models.DateField()
    sequence_order = models.PositiveIntegerField(default=0, help_text="Display/sort order within the academic year")

    class Meta:
        ordering = ["academic_year", "sequence_order", "start_date"]
        constraints = [
            models.UniqueConstraint(fields=["academic_year", "code"], name="exams_unique_code_per_year"),
        ]

    def __str__(self):
        return f"{self.name} ({self.academic_year.label})"


class ExamSubject(TimeStampedModel):
    """
    Per-(exam, class-section, subject) configuration — this MVP's
    flattened stand-in for the approved schema's
    `ExamComponent + ExamComponentSubjectConfig` pair (see Exam's
    docstring). Carries `max_marks`, which every `Mark` row against this
    combination is validated against.

    Deliberately not soft-deletable, same reasoning as ClassSectionSubject/
    TeacherAssignment: a pure configuration row, not a historical fact
    worth preserving after removal.
    """

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="exam_subjects")
    class_section = models.ForeignKey(
        "academics.ClassSection", on_delete=models.PROTECT, related_name="exam_subjects"
    )
    subject = models.ForeignKey("academics.Subject", on_delete=models.PROTECT, related_name="exam_subjects")
    max_marks = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["exam", "class_section", "subject"]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "class_section", "subject"], name="exams_unique_exam_class_section_subject"
            ),
        ]

    def __str__(self):
        return f"{self.exam.code} — {self.class_section} — {self.subject.code} (max {self.max_marks})"
