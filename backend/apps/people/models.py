from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"


class Student(TimeStampedModel, SoftDeleteModel):
    """
    Student profile — see docs/database-schema.md ("User vs. domain profile
    tables") and docs/prototype-analysis.md §2/§3.2 for the field list this
    is based on.

    `user` is a nullable 1:0..1 link to the auth `User` table, per the
    approved schema — not every Student necessarily has login access on day
    one (explicitly confirmed assumption, see prototype-analysis.md's
    "Contradictions / risks" section).

    Fields present in the approved ERD: `admission_no` (unique),
    `first_name`, `last_name`, `dob`, `address`. `gender`, `phone`, and
    `admission_date` are reasonable ERP additions not explicitly listed in
    the ERD's short-form field list but standard for a student record and
    consistent with the level of detail already used elsewhere (e.g.
    AcademicYear's `school` field) — flagged here as an interpretation, not
    silently added.

    Guardian info (`guardian`/`guardianPhone` flat strings in the prototype)
    is deliberately NOT included here — the approved schema normalizes this
    into a standalone `Guardian` + `StudentGuardian` join table (supporting
    multiple guardians per student), which is out of scope for this
    milestone per instruction (Guardian/Teacher modules come later).
    `photo_document_id` (from the ERD) is also deliberately omitted for the
    same reason: the `Document`/S3 storage model doesn't exist yet either.

    Deletion is soft only — same historical-integrity reasoning used
    throughout this codebase (AcademicYear, ClassSection): a "deleted"
    student's Enrollment/Marks/Attendance/Fee history must remain intact and
    queryable, never destroyed.
    """

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profile",
    )
    admission_no = models.CharField(max_length=30, help_text="e.g. 'KHS-2026-0001'")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    dob = models.DateField(verbose_name="Date of birth")
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    admission_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["admission_no"]
        constraints = [
            models.UniqueConstraint(fields=["admission_no"], name="people_unique_admission_no"),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.admission_no})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class EnrollmentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    TRANSFERRED = "transferred", "Transferred"
    GRADUATED = "graduated", "Graduated"


class Enrollment(TimeStampedModel, SoftDeleteModel):
    """
    Links a Student to a ClassSection (which already carries the Academic
    Year) for a given year — see docs/database-schema.md's
    "Class / Section / ClassSection / Enrollment" section:
    `(student_id, class_section_id, roll_no, status)`.

    `roll_no` uniqueness is enforced by a DB constraint scoped to
    `class_section_id` — this is the actual fix for the prototype's
    data-integrity gap (§17/§2 of prototype-analysis.md), where roll numbers
    were freely editable text with zero uniqueness check.

    A student's promotion to a new year creates a NEW Enrollment row (new
    `class_section`, since ClassSection is year-scoped); it never modifies
    or deletes the previous year's row — that's why `(student, class_section)`
    is also unique here (a student can't be enrolled twice in the exact same
    year's offering) but a student CAN have multiple Enrollment rows total,
    one per year they've been enrolled.

    Soft delete only, for the same historical-integrity reason as
    everywhere else in this codebase.
    """

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="enrollments")
    class_section = models.ForeignKey(
        "academics.ClassSection", on_delete=models.PROTECT, related_name="enrollments"
    )
    roll_no = models.PositiveIntegerField()
    status = models.CharField(max_length=15, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE)

    class Meta:
        ordering = ["class_section", "roll_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["class_section", "roll_no"], name="people_unique_roll_no_per_class_section"
            ),
            models.UniqueConstraint(
                fields=["student", "class_section"], name="people_unique_student_per_class_section"
            ),
        ]

    def __str__(self):
        return f"{self.student.full_name} — {self.class_section} (Roll {self.roll_no})"
