from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel


class Mark(TimeStampedModel, SoftDeleteModel):
    """
    One student's obtained marks for one (exam, class-section, subject)
    configuration — see docs/prototype-analysis.md §17.2's field list:
    "Mark — id, student_id, exam_component_id, subject_id, marks_obtained
    (decimal), entered_by_id, entered_at, updated_at. Unique constraint on
    (student_id, exam_component_id, subject_id)."

    This MVP references `ExamSubject` (this codebase's flattened stand-in
    for `ExamComponent` + `ExamComponentSubjectConfig` — see
    apps.exams.models.Exam's docstring for why) instead of a separate
    `exam_component_id` + `subject_id` pair; `ExamSubject` already uniquely
    identifies the (exam, class_section, subject) combination and carries
    the `max_marks` this is validated against, so one FK does the job of
    both documented fields. Unique constraint is (student, exam_subject) —
    the direct MVP equivalent of the documented (student, exam_component,
    subject) uniqueness rule, and exactly what "prevent duplicate marks for
    the same student/subject/exam" means here.

    No grading, ranking, pass/fail computation, or report-card rollup is
    computed or stored anywhere in this app — explicitly out of scope for
    this batch (docs/prototype-analysis.md §5-§9's compensatory pass-fail
    formula and ranking logic belong to the future Report Cards module).

    Soft delete only, same historical-integrity reasoning as every other
    model in this codebase.
    """

    student = models.ForeignKey("people.Student", on_delete=models.PROTECT, related_name="marks")
    exam_subject = models.ForeignKey("exams.ExamSubject", on_delete=models.PROTECT, related_name="marks")
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])
    entered_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="marks_entered"
    )
    entered_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["exam_subject", "student"]
        constraints = [
            models.UniqueConstraint(fields=["student", "exam_subject"], name="marks_unique_student_exam_subject"),
        ]

    def __str__(self):
        return f"{self.student.full_name} — {self.exam_subject} = {self.marks_obtained}"
