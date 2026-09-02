from django.contrib import admin

from apps.attendance.models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ["student", "class_section", "date", "status", "marked_by", "marked_at", "deleted_at"]
    list_filter = ["status", "date", "class_section__academic_year"]
    search_fields = ["student__admission_no", "student__first_name", "student__last_name"]
