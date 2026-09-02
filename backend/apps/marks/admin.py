from django.contrib import admin

from apps.marks.models import Mark


@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ["student", "exam_subject", "marks_obtained", "entered_by", "entered_at", "deleted_at"]
    list_filter = ["exam_subject__exam"]
    search_fields = ["student__admission_no", "student__first_name", "student__last_name"]
