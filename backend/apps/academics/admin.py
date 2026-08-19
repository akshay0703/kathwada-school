from django.contrib import admin

from apps.academics.models import AcademicYear


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ["label", "school", "start_date", "end_date", "is_current", "deleted_at"]
    list_filter = ["school", "is_current"]
    search_fields = ["label", "school"]
