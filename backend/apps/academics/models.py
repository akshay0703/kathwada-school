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


class SchoolClass(TimeStampedModel, SoftDeleteModel):
    """
    A grade level, e.g. "Std 10" — see docs/database-schema.md's
    "Class / Section / ClassSection / Enrollment" section. Named
    `SchoolClass` rather than `Class` purely to avoid the awkwardness of a
    model literally named after a language keyword-adjacent builtin
    (`class` is a reserved word; `Class` as an identifier is legal Python
    but shadows nothing intentionally and reads badly throughout the
    codebase, e.g. `Class.objects`). This is a naming choice only — the
    entity is exactly the ERD's CLASS.

    Deliberately NOT year-scoped: "Std 10" itself doesn't change year to
    year, only its per-year offering (`ClassSection`) does.
    """

    name = models.CharField(max_length=50, help_text="e.g. 'Std 10'")
    order = models.PositiveIntegerField(
        default=0, help_text="Display/sort order (e.g. 1 for Std 1, 10 for Std 10), independent of name text."
    )

    class Meta:
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="academics_unique_class_name"),
        ]

    def __str__(self):
        return self.name


class Section(TimeStampedModel, SoftDeleteModel):
    """
    A section label, e.g. "A" — modeled separately from SchoolClass so the
    same Section name can be reused across different classes (per
    docs/database-schema.md). A standalone registry of reusable labels, not
    itself year- or class-scoped.
    """

    name = models.CharField(max_length=20, help_text="e.g. 'A'")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="academics_unique_section_name"),
        ]

    def __str__(self):
        return self.name


class Subject(TimeStampedModel, SoftDeleteModel):
    """
    A teachable subject, e.g. "Mathematics" — standalone entity, offered to
    class-sections via `ClassSectionSubject` (see below).
    """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, help_text="Short code, e.g. 'MATH'")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="academics_unique_subject_name"),
            models.UniqueConstraint(fields=["code"], name="academics_unique_subject_code"),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class ClassSection(TimeStampedModel, SoftDeleteModel):
    """
    The actual per-year offering — "Std 10-A in 2026-27" — per
    docs/database-schema.md: `(class_id, section_id, academic_year_id,
    class_teacher_id)`. This is what Enrollment (Milestone 2) will attach
    students to.

    `class_teacher` is a nullable FK straight to the auth `User` model, not
    to a `Teacher` profile — no `Teacher` entity exists yet (people app is
    still an empty stub; Teacher/Guardian modules are explicitly out of
    scope for this milestone per instruction). This is an interim choice,
    consistent with how `AcademicYear.school` handled a similarly
    not-yet-built dependency in Phase 1.1: it satisfies the literal
    "class_teacher_id" field requirement without inventing a Teacher entity
    that hasn't been approved/built yet. Expected to be swapped to a
    Teacher-profile FK once that module exists.

    Soft delete only (never hard) — same historical-integrity reasoning as
    AcademicYear: a class-section that's been retired should stay queryable
    for any Enrollment/Marks/Attendance rows that will eventually reference
    it, not vanish.
    """

    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name="class_sections")
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="class_sections")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name="class_sections")
    class_teacher = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_sections_led",
    )
    subjects = models.ManyToManyField(Subject, through="ClassSectionSubject", related_name="class_sections")

    class Meta:
        ordering = ["-academic_year__start_date", "school_class__order", "section__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "section", "academic_year"],
                name="academics_unique_class_section_per_year",
            ),
        ]

    def __str__(self):
        return f"{self.school_class.name}-{self.section.name} ({self.academic_year.label})"


class ClassSectionSubject(TimeStampedModel):
    """
    Join table: which subjects a given ClassSection offers — the ERD's
    "CLASS_SECTION }o--o{ SUBJECT : offers" relationship
    (docs/database-schema.md). Deliberately not soft-deletable itself (it's a
    pure association row, not a historical fact worth preserving after
    removal) — removing a subject from a class-section's offering is a real
    delete; the ClassSection and Subject rows it links remain fully intact
    either way.
    """

    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name="subject_links")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="class_section_links")

    class Meta:
        ordering = ["subject__name"]
        constraints = [
            models.UniqueConstraint(fields=["class_section", "subject"], name="academics_unique_class_section_subject"),
        ]

    def __str__(self):
        return f"{self.class_section} — {self.subject.code}"
