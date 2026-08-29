from rest_framework import serializers

from apps.academics.models import (
    AcademicYear,
    ClassSection,
    ClassSectionSubject,
    SchoolClass,
    Section,
    Subject,
)


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ["id", "school", "label", "start_date", "end_date", "is_current", "created_at", "updated_at"]
        read_only_fields = ["id", "is_current", "created_at", "updated_at"]
        # is_current is deliberately read-only here — it's set only via the
        # dedicated mark-current action (apps/academics/views.py), which
        # atomically unsets every sibling row first. Allowing it through
        # plain create/update would bypass that atomicity and rely solely on
        # the DB constraint rejecting the second row, which is a worse user
        # experience (a raw IntegrityError instead of a clean flow).

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        school = attrs.get("school", getattr(self.instance, "school", None)) or "Kathwada High School"

        if start and end and start >= end:
            raise serializers.ValidationError({"end_date": "end_date must be after start_date."})

        if start and end:
            overlapping = AcademicYear.objects.filter(
                school=school, start_date__lte=end, end_date__gte=start
            )
            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            conflict = overlapping.first()
            if conflict:
                raise serializers.ValidationError(
                    {"non_field_errors": [f"Date range overlaps with existing academic year '{conflict.label}'."]}
                )

        return attrs


class SchoolClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolClass
        fields = ["id", "name", "order", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "code", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClassSectionSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)

    class Meta:
        model = ClassSectionSubject
        fields = ["id", "subject", "subject_name", "subject_code"]
        read_only_fields = ["id", "subject_name", "subject_code"]


class ClassSectionSerializer(serializers.ModelSerializer):
    """
    Read side includes denormalized display fields (`school_class_name`,
    `section_name`, `academic_year_label`) so the ERP UI doesn't need N+1
    follow-up requests just to render a readable label — write side only
    accepts the underlying FK ids.
    """

    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    academic_year_label = serializers.CharField(source="academic_year.label", read_only=True)
    class_teacher_email = serializers.CharField(source="class_teacher.email", read_only=True, default=None)
    subjects = ClassSectionSubjectSerializer(source="subject_links", many=True, read_only=True)

    class Meta:
        model = ClassSection
        fields = [
            "id",
            "school_class",
            "school_class_name",
            "section",
            "section_name",
            "academic_year",
            "academic_year_label",
            "class_teacher",
            "class_teacher_email",
            "subjects",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "school_class_name",
            "section_name",
            "academic_year_label",
            "class_teacher_email",
            "subjects",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        school_class = attrs.get("school_class", getattr(self.instance, "school_class", None))
        section = attrs.get("section", getattr(self.instance, "section", None))
        academic_year = attrs.get("academic_year", getattr(self.instance, "academic_year", None))

        if school_class and section and academic_year:
            conflict = ClassSection.objects.filter(
                school_class=school_class, section=section, academic_year=academic_year
            )
            if self.instance:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            f"'{school_class} - {section}' already exists for academic year '{academic_year.label}'."
                        ]
                    }
                )
        return attrs
