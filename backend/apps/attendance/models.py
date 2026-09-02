from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    ABSENT = "absent", "Absent"
    LATE = "late", "Late"
    EXCUSED = "excused", "Excused"


class AttendanceRecord(TimeStampedModel, SoftDeleteModel):
    """
    One student's attendance status for one day — see docs/database-schema.md's
    ERD (`STUDENT ||--o{ ATTENDANCE_RECORD`, `CLASS_SECTION ||--o{
    ATTENDANCE_RECORD`, `USER ||--o{ ATTENDANCE_RECORD : "marked_by"`) and
    docs/prototype-analysis.md §3.2's exact field list: "AttendanceRecord —
    id, student_id, class_section_id, date, status (present/absent/late/
    excused), marked_by_id, marked_at. Unique on (student_id, date)."

    Every field name and the four-way status enum, and the (student, date)
    uniqueness rule, are transcribed directly from that spec — this is what
    "Prevent duplicate attendance records for the same student/date"
    actually means at the schema level: one status per student per calendar
    day, full stop, regardless of which class_section it's recorded against.
    (The prototype only ever supported binary Present/Absent — see
    prototype-analysis.md's "Needs normalization" table — but the approved
    schema already extends that to Late/Excused, so this uses the full
    4-way enum rather than re-narrowing to just P/A.)

    There is deliberately no separate "AttendanceSession" model: the
    approved ERD has no such entity, and grouping AttendanceRecord rows by
    (class_section, date) via a query already gives every piece of
    "session" behaviour this milestone asks for (view by class-section and
    date, mark for all enrolled students in one action) without inventing
    an entity the schema doesn't call for. See
    AttendanceRecordViewSet.bulk_mark for the "mark for a whole class-section
    on a date" action.

    `class_section` is stored explicitly (not just derived from the
    student's current Enrollment) because the ERD models it as its own FK —
    this also means a correction to which class-section a record belongs to
    doesn't require touching Enrollment history.

    `marked_by` is nullable (SET_NULL) since a user account could later be
    removed without invalidating historical attendance data — same pattern
    as every other "who did this" FK in this codebase.

    Soft delete only, same historical-integrity reasoning as every other
    model here — a corrected/retracted attendance entry should stay
    queryable, not disappear.
    """

    student = models.ForeignKey("people.Student", on_delete=models.PROTECT, related_name="attendance_records")
    class_section = models.ForeignKey(
        "academics.ClassSection", on_delete=models.PROTECT, related_name="attendance_records"
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=AttendanceStatus.choices)
    marked_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records_marked",
    )
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "class_section", "student"]
        constraints = [
            models.UniqueConstraint(fields=["student", "date"], name="attendance_unique_student_per_date"),
        ]

    def __str__(self):
        return f"{self.student.full_name} — {self.date} ({self.status})"
