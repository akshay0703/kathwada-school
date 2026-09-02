from rest_framework import serializers

from apps.exams.models import ExamSubject
from apps.marks.models import Mark
from apps.people.models import Student


class MarkSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_admission_no = serializers.CharField(source="student.admission_no", read_only=True)
    exam_name = serializers.CharField(source="exam_subject.exam.name", read_only=True)
    subject_name = serializers.CharField(source="exam_subject.subject.name", read_only=True)
    subject_code = serializers.CharField(source="exam_subject.subject.code", read_only=True)
    max_marks = serializers.DecimalField(source="exam_subject.max_marks", max_digits=6, decimal_places=2, read_only=True)
    entered_by_email = serializers.CharField(source="entered_by.email", read_only=True, default=None)

    class Meta:
        model = Mark
        fields = [
            "id",
            "student",
            "student_name",
            "student_admission_no",
            "exam_subject",
            "exam_name",
            "subject_name",
            "subject_code",
            "max_marks",
            "marks_obtained",
            "entered_by",
            "entered_by_email",
            "entered_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_name",
            "student_admission_no",
            "exam_name",
            "subject_name",
            "subject_code",
            "max_marks",
            "entered_by",
            "entered_by_email",
            "entered_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        student = attrs.get("student", getattr(self.instance, "student", None))
        exam_subject = attrs.get("exam_subject", getattr(self.instance, "exam_subject", None))
        marks_obtained = attrs.get("marks_obtained", getattr(self.instance, "marks_obtained", None))

        if exam_subject and marks_obtained is not None and marks_obtained > exam_subject.max_marks:
            raise serializers.ValidationError(
                {"marks_obtained": [f"Cannot exceed the maximum of {exam_subject.max_marks} for this subject."]}
            )

        if student and exam_subject:
            is_actively_enrolled = student.enrollments.filter(
                class_section=exam_subject.class_section, status="active"
            ).exists()
            if not is_actively_enrolled:
                raise serializers.ValidationError(
                    {"student": [f"{student.full_name} is not actively enrolled in this exam's class-section."]}
                )

            conflict = Mark.objects.filter(student=student, exam_subject=exam_subject)
            if self.instance:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": [f"A mark already exists for {student.full_name} in this exam subject."]}
                )

        return attrs

    def create(self, validated_data):
        validated_data["entered_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["entered_by"] = self.context["request"].user
        return super().update(instance, validated_data)


class BulkMarkEntrySerializer(serializers.Serializer):
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())
    marks_obtained = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=0)


class BulkMarkSaveSerializer(serializers.Serializer):
    """
    Input shape for MarkViewSet.bulk_save — saves (or corrects) marks for
    every listed student against one exam_subject in a single request,
    which is what "Student marks entry interface" / "Save/update marks"
    means in practice for a teacher entering a whole class-section's marks
    for one subject at once. Mirrors AttendanceRecordViewSet.bulk_mark's
    shape/approach exactly.
    """

    exam_subject = serializers.PrimaryKeyRelatedField(queryset=ExamSubject.objects.all())
    records = BulkMarkEntrySerializer(many=True)

    def validate(self, attrs):
        exam_subject = attrs["exam_subject"]
        actively_enrolled_ids = set(
            exam_subject.class_section.enrollments.filter(status="active").values_list("student_id", flat=True)
        )
        bad_students = [r["student"] for r in attrs["records"] if r["student"].id not in actively_enrolled_ids]
        if bad_students:
            names = ", ".join(s.full_name for s in bad_students)
            raise serializers.ValidationError(
                {"records": [f"Not actively enrolled in this exam's class-section: {names}."]}
            )
        over_max = [r for r in attrs["records"] if r["marks_obtained"] > exam_subject.max_marks]
        if over_max:
            raise serializers.ValidationError(
                {"records": [f"marks_obtained cannot exceed the maximum of {exam_subject.max_marks}."]}
            )
        return attrs

    def save(self, entered_by):
        exam_subject = self.validated_data["exam_subject"]
        results = []
        for record in self.validated_data["records"]:
            obj, _ = Mark.all_with_deleted.update_or_create(
                student=record["student"],
                exam_subject=exam_subject,
                defaults={"marks_obtained": record["marks_obtained"], "entered_by": entered_by, "deleted_at": None},
            )
            results.append(obj)
        return results
