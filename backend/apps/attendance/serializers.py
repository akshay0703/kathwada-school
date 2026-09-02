from rest_framework import serializers

from apps.academics.models import ClassSection
from apps.attendance.models import AttendanceRecord, AttendanceStatus
from apps.people.models import Student


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_admission_no = serializers.CharField(source="student.admission_no", read_only=True)
    school_class_name = serializers.CharField(source="class_section.school_class.name", read_only=True)
    section_name = serializers.CharField(source="class_section.section.name", read_only=True)
    academic_year_label = serializers.CharField(source="class_section.academic_year.label", read_only=True)
    marked_by_email = serializers.CharField(source="marked_by.email", read_only=True, default=None)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "student",
            "student_name",
            "student_admission_no",
            "class_section",
            "school_class_name",
            "section_name",
            "academic_year_label",
            "date",
            "status",
            "marked_by",
            "marked_by_email",
            "marked_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_name",
            "student_admission_no",
            "school_class_name",
            "section_name",
            "academic_year_label",
            "marked_by",
            "marked_by_email",
            "marked_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        student = attrs.get("student", getattr(self.instance, "student", None))
        class_section = attrs.get("class_section", getattr(self.instance, "class_section", None))
        date = attrs.get("date", getattr(self.instance, "date", None))

        if student and class_section:
            is_actively_enrolled = student.enrollments.filter(class_section=class_section, status="active").exists()
            if not is_actively_enrolled:
                raise serializers.ValidationError(
                    {"student": [f"{student.full_name} is not actively enrolled in this class-section."]}
                )

        if student and date:
            conflict = AttendanceRecord.objects.filter(student=student, date=date)
            if self.instance:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": [f"An attendance record already exists for {student.full_name} on {date}."]}
                )

        return attrs

    def create(self, validated_data):
        validated_data["marked_by"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["marked_by"] = self.context["request"].user
        return super().update(instance, validated_data)


class BulkMarkRecordSerializer(serializers.Serializer):
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())
    status = serializers.ChoiceField(choices=AttendanceStatus.choices)


class BulkMarkSerializer(serializers.Serializer):
    """
    Input shape for AttendanceRecordViewSet.bulk_mark — marks (or
    re-marks/corrects) attendance for a whole class-section on one date in
    a single request, which is what "mark attendance for all active
    enrolled students" means in practice for a teacher taking daily
    attendance.
    """

    class_section = serializers.PrimaryKeyRelatedField(queryset=ClassSection.objects.all())
    date = serializers.DateField()
    records = BulkMarkRecordSerializer(many=True)

    def validate(self, attrs):
        class_section = attrs["class_section"]
        actively_enrolled_ids = set(
            class_section.enrollments.filter(status="active").values_list("student_id", flat=True)
        )
        bad_students = [
            r["student"] for r in attrs["records"] if r["student"].id not in actively_enrolled_ids
        ]
        if bad_students:
            names = ", ".join(s.full_name for s in bad_students)
            raise serializers.ValidationError(
                {"records": [f"Not actively enrolled in this class-section: {names}."]}
            )
        return attrs

    def save(self, marked_by):
        class_section = self.validated_data["class_section"]
        date = self.validated_data["date"]
        results = []
        for record in self.validated_data["records"]:
            obj, _ = AttendanceRecord.all_with_deleted.update_or_create(
                student=record["student"],
                date=date,
                defaults={
                    "class_section": class_section,
                    "status": record["status"],
                    "marked_by": marked_by,
                    "deleted_at": None,
                },
            )
            results.append(obj)
        return results
