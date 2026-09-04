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


class Teacher(TimeStampedModel, SoftDeleteModel):
    """
    Teacher profile — see docs/database-schema.md's ERD (`USER ||--o| TEACHER`)
    and docs/prototype-analysis.md §3.2: "Teacher — id, user_id, first_name,
    last_name, phone, email, joined_date." Field list transcribed directly
    from there, same as Student's fields were.

    `user` is nullable, same reasoning as `Student.user`: not every Teacher
    necessarily has login access on day one (explicitly confirmed assumption
    in prototype-analysis.md's "Contradictions / risks" section, which
    applies to Teacher/Guardian/Staff the same way it does to Student).

    `email` here is the teacher's own contact-info field (per the ERD's
    explicit field list), separate from `user.email` (the login identity) —
    a Teacher profile can exist, and be edited, before or without ever
    having a User login attached.

    Deliberately NOT changed by this milestone: `ClassSection.class_teacher`
    (apps/academics/models.py) still points at `accounts.User`, not at this
    Teacher model, even though that field's docstring flags it as an interim
    choice "expected to be swapped to a Teacher-profile FK once that module
    exists." Making that swap now would require an additional migration
    touching Milestone 1's already-shipped, already-tested ClassSection
    model/serializer/view/frontend — out of scope for "implement Teacher
    Management as one focused batch, do not redesign existing architecture."
    Flagged here explicitly as a known, deliberate follow-up, not silently
    ignored.

    Soft delete only, same historical-integrity reasoning as every other
    model in this codebase — a "deleted" teacher's TeacherAssignment history
    (and eventually Marks entered_by, Attendance marked_by, etc.) must
    remain intact and queryable.
    """

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teacher_profile",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    joined_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["first_name", "last_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class TeacherAssignment(TimeStampedModel):
    """
    Join table: which Teacher teaches which (ClassSection, Subject) pairing
    — the ERD's "TEACHER }o--o{ CLASS_SECTION_SUBJECT: assigned to (via
    TEACHER_ASSIGNMENT)" relationship, and prototype-analysis.md §3.2's
    "TeacherAssignment — teacher_id, class_section_subject_id." This is what
    scopes a Teacher's future Marks/Attendance access to only their assigned
    classes/subjects (prototype-analysis.md's permission notes) — that
    scoping enforcement itself is not implemented yet (it belongs to the
    Marks/Attendance modules, out of scope here), but this table is the
    foundation it will be built on, per the approved schema.

    Deliberately not soft-deletable itself, same reasoning as
    ClassSectionSubject: it's a pure association row, not a historical fact
    worth preserving after removal — removing an assignment is a real
    delete; the Teacher and ClassSectionSubject rows it links remain intact.
    """

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="assignments")
    class_section_subject = models.ForeignKey(
        "academics.ClassSectionSubject", on_delete=models.CASCADE, related_name="teacher_assignments"
    )

    class Meta:
        ordering = ["teacher__first_name", "teacher__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "class_section_subject"], name="people_unique_teacher_assignment"
            ),
        ]

    def __str__(self):
        return f"{self.teacher.full_name} — {self.class_section_subject}"


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


class GuardianRelationship(models.TextChoices):
    FATHER = "father", "Father"
    MOTHER = "mother", "Mother"
    GUARDIAN = "guardian", "Guardian"
    OTHER = "other", "Other"


class Guardian(TimeStampedModel, SoftDeleteModel):
    """
    A parent/guardian profile — see docs/database-schema.md's ERD
    (`USER ||--o| GUARDIAN`) and docs/prototype-analysis.md §17.2's field
    list: "Guardian — id, user_id (nullable), name, phone, email,
    relationship."

    Standalone entity (not a flat string on Student, as in the prototype —
    see prototype-analysis.md's normalization note), linked to Student via
    `StudentGuardian` below, which is what actually enables multiple
    guardians per student.

    `user` is nullable, same reasoning as Student/Teacher: a Guardian
    profile can exist (e.g. entered by office staff during admission)
    before or without ever having a Parent login attached.

    Soft delete only, same historical-integrity reasoning as everywhere
    else in this codebase.
    """

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guardian_profile",
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    relationship = models.CharField(max_length=10, choices=GuardianRelationship.choices, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StudentGuardian(TimeStampedModel):
    """
    Join table: links a Student to a Guardian, with an `is_primary_contact`
    flag — see docs/database-schema.md's "Guardian / StudentGuardian"
    section and prototype-analysis.md §17.2: "StudentGuardian (join) —
    student_id, guardian_id, is_primary_contact." This is what supports
    multiple guardians per student (the prototype supported exactly one
    flat `guardian`/`guardianPhone` string pair — see
    prototype-analysis.md §2).

    This table is also the mechanism docs/permissions.md's "Scoping rules"
    section names explicitly: "Parent → own child's ... records only ...
    filtered via StudentGuardian to the children linked to that Parent's
    account." See `guardian_child_student_ids()` below, used by every
    other app's Parent-role queryset scoping (Student, Enrollment,
    Attendance, Marks, Fees) to resolve that filter — this is the piece
    those modules' docstrings flagged as "StudentGuardian doesn't exist
    yet" when they were built.

    Deliberately not soft-deletable, same reasoning as ClassSectionSubject/
    TeacherAssignment: a pure association row, not a historical fact worth
    preserving after removal.
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="student_guardians")
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name="student_guardians")
    is_primary_contact = models.BooleanField(default=False)

    class Meta:
        ordering = ["student", "-is_primary_contact"]
        constraints = [
            models.UniqueConstraint(fields=["student", "guardian"], name="people_unique_student_guardian"),
        ]

    def __str__(self):
        primary = " (primary)" if self.is_primary_contact else ""
        return f"{self.guardian.name} — {self.student.full_name}{primary}"


def guardian_child_student_ids(user):
    """
    Every child Student id linked (via StudentGuardian) to the Guardian
    profile owned by `user` — the shared resolution for the "Parent → own
    child's records only" scoping rule (docs/permissions.md's "Scoping
    rules" section) used across apps.people, apps.attendance, apps.marks,
    and apps.fees. Returns an empty set (not an error) for a user with no
    linked Guardian profile at all.
    """
    return set(
        StudentGuardian.objects.filter(guardian__user=user).values_list("student_id", flat=True)
    )
