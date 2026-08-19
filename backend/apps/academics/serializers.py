from rest_framework import serializers

from apps.academics.models import AcademicYear


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
