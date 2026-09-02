from rest_framework import serializers

from apps.exams.models import Exam, ExamSubject


class ExamSubjectSerializer(serializers.ModelSerializer):
    """
    Nested read-only under ExamSerializer's `exam_subjects`, and also
    exposed directly at /api/v1/exam-subjects/ for configuring which
    (class-section, subject) pairs an exam has, and their max marks.
    """

    school_class_name = serializers.CharField(source="class_section.school_class.name", read_only=True)
    section_name = serializers.CharField(source="class_section.section.name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)
    exam_name = serializers.CharField(source="exam.name", read_only=True)

    class Meta:
        model = ExamSubject
        fields = [
            "id",
            "exam",
            "exam_name",
            "class_section",
            "school_class_name",
            "section_name",
            "subject",
            "subject_name",
            "subject_code",
            "max_marks",
        ]
        read_only_fields = ["id", "exam_name", "school_class_name", "section_name", "subject_name", "subject_code"]


class ExamSerializer(serializers.ModelSerializer):
    academic_year_label = serializers.CharField(source="academic_year.label", read_only=True)
    exam_subjects = ExamSubjectSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = [
            "id",
            "academic_year",
            "academic_year_label",
            "code",
            "name",
            "start_date",
            "end_date",
            "sequence_order",
            "exam_subjects",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "academic_year_label", "exam_subjects", "created_at", "updated_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": ["End date cannot be before start date."]})
        return attrs


class ExamListSerializer(serializers.ModelSerializer):
    """Lighter-weight list serializer, omitting the nested exam_subjects."""

    academic_year_label = serializers.CharField(source="academic_year.label", read_only=True)
    subject_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            "id",
            "academic_year",
            "academic_year_label",
            "code",
            "name",
            "start_date",
            "end_date",
            "sequence_order",
            "subject_count",
        ]

    def get_subject_count(self, obj):
        return obj.exam_subjects.count()
