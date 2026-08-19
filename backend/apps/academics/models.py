from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel


class AcademicYear(TimeStampedModel, SoftDeleteModel):
    """
    First-class Academic Year entity — see docs/database-schema.md's
    "Academic Year — first-class, never overwritten" section. Every
    year-scoped fact in the system (ClassSection, Enrollment, Exam, Mark,
    AttendanceRecord, FeeInvoice) will carry a foreign key to this model in
    later phases; this model itself carries no such downstream references
    yet, since Phase 1.1 is scoped to Academic Years only.

    `school` is a plain default-valued field, not a foreign key to a School
    model — no School entity exists anywhere in the approved schema
    (docs/database-schema.md), since this is a single-school system by
    design. This satisfies the literal field requirement without expanding
    the schema into multi-tenancy that was never approved. Flagged
    explicitly in the Phase 1.1 handoff doc as an interpretation choice.

    Deletion is soft (via SoftDeleteModel, inherited) — never hard —
    specifically because "historical academic years must remain intact" is
    a hard requirement, not just a policy to remember. A soft-deleted
    academic year disappears from normal querysets but the row, and
    everything that will eventually reference it, is never destroyed.
    """

    school = models.CharField(max_length=200, default="Kathwada High School")
    label = models.CharField(max_length=50, help_text="e.g. '2026-27'")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            # DB-enforced: at most one row per school can have is_current=True.
            # This is a Postgres/SQLite partial unique index (condition=...),
            # not a plain unique field — is_current=False rows are unlimited,
            # only True values collide. This is the actual mechanism behind
            # "only one academic year can be current for a school" — not
            # merely application-level discipline.
            models.UniqueConstraint(
                fields=["school"],
                condition=models.Q(is_current=True),
                name="academics_one_current_year_per_school",
            ),
            # Prevents two academic years for the same school sharing a label
            # (e.g. two rows both labeled "2026-27").
            models.UniqueConstraint(
                fields=["school", "label"],
                name="academics_unique_label_per_school",
            ),
            # DB-enforced: end_date must be strictly after start_date.
            # Overlap-between-different-years checking (a range-exclusion
            # problem) is deliberately NOT a DB constraint here — a portable
            # version working identically on both Postgres and SQLite (this
            # project's test/dev database) isn't practical without a
            # Postgres-only extension (btree_gist + EXCLUDE USING gist).
            # Overlap is enforced at the serializer layer instead — see
            # apps/academics/serializers.py.
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F("start_date")),
                name="academics_end_date_after_start_date",
            ),
        ]

    def __str__(self):
        return f"{self.label} ({self.school})"
