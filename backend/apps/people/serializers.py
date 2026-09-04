from rest_framework import serializers

from apps.people.models import Enrollment, Guardian, Student, StudentGuardian, Teacher, TeacherAssignment


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Nested read-only under StudentSerializer's `enrollments`, and also
    exposed directly at /api/v1/enrollments/ for creating/editing a single
    enrollment (e.g. promoting a student to a new class-section).
    """

    school_class_name = serializers.CharField(source="class_section.school_class.name", read_only=True)
    section_name = serializers.CharField(source="class_section.section.name", read_only=True)
    academic_year_label = serializers.CharField(source="class_section.academic_year.label", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_admission_no = serializers.CharField(source="student.admission_no", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "student",
            "student_name",
            "student_admission_no",
            "class_section",
            "school_class_name",
            "section_name",
            "academic_year_label",
            "roll_no",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "school_class_name",
            "section_name",
            "academic_year_label",
            "student_name",
            "student_admission_no",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        student = attrs.get("student", getattr(self.instance, "student", None))
        class_section = attrs.get("class_section", getattr(self.instance, "class_section", None))
        roll_no = attrs.get("roll_no", getattr(self.instance, "roll_no", None))

        if class_section and roll_no:
            roll_conflict = Enrollment.objects.filter(class_section=class_section, roll_no=roll_no)
            if self.instance:
                roll_conflict = roll_conflict.exclude(pk=self.instance.pk)
            if roll_conflict.exists():
                raise serializers.ValidationError(
                    {"roll_no": [f"Roll number {roll_no} is already taken in this class-section."]}
                )

        if student and class_section:
            student_conflict = Enrollment.objects.filter(student=student, class_section=class_section)
            if self.instance:
                student_conflict = student_conflict.exclude(pk=self.instance.pk)
            if student_conflict.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": ["This student is already enrolled in this class-section."]}
                )

        return attrs


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    enrollments = EnrollmentSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "user",
            "admission_no",
            "first_name",
            "last_name",
            "full_name",
            "dob",
            "gender",
            "address",
            "phone",
            "admission_date",
            "enrollments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "full_name", "enrollments", "created_at", "updated_at"]


class StudentListSerializer(serializers.ModelSerializer):
    """
    Lighter-weight serializer for the list view — omits the nested
    enrollments list (which the list page doesn't need) to keep the list
    endpoint fast as the student count grows.
    """

    full_name = serializers.CharField(read_only=True)
    current_class_section = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "admission_no",
            "first_name",
            "last_name",
            "full_name",
            "dob",
            "gender",
            "phone",
            "current_class_section",
        ]

    def get_current_class_section(self, obj):
        enrollment = (
            obj.enrollments.filter(status="active").select_related("class_section__school_class", "class_section__section", "class_section__academic_year").order_by("-class_section__academic_year__start_date").first()
        )
        if not enrollment:
            return None
        cs = enrollment.class_section
        return {
            "id": cs.id,
            "label": f"{cs.school_class.name}-{cs.section.name} ({cs.academic_year.label})",
            "roll_no": enrollment.roll_no,
        }


class TeacherAssignmentSerializer(serializers.ModelSerializer):
    """
    Nested read-only under TeacherSerializer's `assignments`, and also
    exposed directly at /api/v1/teacher-assignments/ for assigning/
    unassigning a teacher to a (class-section, subject) pairing.
    """

    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    subject_name = serializers.CharField(source="class_section_subject.subject.name", read_only=True)
    subject_code = serializers.CharField(source="class_section_subject.subject.code", read_only=True)
    school_class_name = serializers.CharField(
        source="class_section_subject.class_section.school_class.name", read_only=True
    )
    section_name = serializers.CharField(source="class_section_subject.class_section.section.name", read_only=True)
    academic_year_label = serializers.CharField(
        source="class_section_subject.class_section.academic_year.label", read_only=True
    )

    class Meta:
        model = TeacherAssignment
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "class_section_subject",
            "subject_name",
            "subject_code",
            "school_class_name",
            "section_name",
            "academic_year_label",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "teacher_name",
            "subject_name",
            "subject_code",
            "school_class_name",
            "section_name",
            "academic_year_label",
            "created_at",
        ]

    def validate(self, attrs):
        teacher = attrs.get("teacher", getattr(self.instance, "teacher", None))
        class_section_subject = attrs.get(
            "class_section_subject", getattr(self.instance, "class_section_subject", None)
        )
        if teacher and class_section_subject:
            conflict = TeacherAssignment.objects.filter(teacher=teacher, class_section_subject=class_section_subject)
            if self.instance:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": ["This teacher is already assigned to this class-section subject."]}
                )
        return attrs


class TeacherSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    assignments = TeacherAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Teacher
        fields = [
            "id",
            "user",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "joined_date",
            "assignments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "full_name", "assignments", "created_at", "updated_at"]


class TeacherListSerializer(serializers.ModelSerializer):
    """
    Lighter-weight serializer for the list view — omits the nested
    assignments list, same reasoning as StudentListSerializer.
    """

    full_name = serializers.CharField(read_only=True)
    assignment_count = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ["id", "first_name", "last_name", "full_name", "phone", "email", "joined_date", "assignment_count"]

    def get_assignment_count(self, obj):
        return obj.assignments.count()


class StudentGuardianSerializer(serializers.ModelSerializer):
    """
    Nested read-only under GuardianSerializer's `student_links`, and also
    exposed directly at /api/v1/student-guardians/ for linking/unlinking a
    guardian to a student.
    """

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_admission_no = serializers.CharField(source="student.admission_no", read_only=True)
    guardian_name = serializers.CharField(source="guardian.name", read_only=True)

    class Meta:
        model = StudentGuardian
        fields = ["id", "student", "student_name", "student_admission_no", "guardian", "guardian_name", "is_primary_contact"]
        read_only_fields = ["id", "student_name", "student_admission_no", "guardian_name"]

    def validate(self, attrs):
        student = attrs.get("student", getattr(self.instance, "student", None))
        guardian = attrs.get("guardian", getattr(self.instance, "guardian", None))
        if student and guardian:
            conflict = StudentGuardian.objects.filter(student=student, guardian=guardian)
            if self.instance:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": [f"{guardian.name} is already linked to {student.full_name}."]}
                )
        return attrs


class GuardianSerializer(serializers.ModelSerializer):
    student_links = StudentGuardianSerializer(source="student_guardians", many=True, read_only=True)

    class Meta:
        model = Guardian
        fields = ["id", "user", "name", "phone", "email", "relationship", "student_links", "created_at", "updated_at"]
        read_only_fields = ["id", "student_links", "created_at", "updated_at"]


class GuardianListSerializer(serializers.ModelSerializer):
    """Lighter-weight list serializer, omitting the nested student_links."""

    child_count = serializers.SerializerMethodField()

    class Meta:
        model = Guardian
        fields = ["id", "name", "phone", "email", "relationship", "child_count"]

    def get_child_count(self, obj):
        return obj.student_guardians.count()
