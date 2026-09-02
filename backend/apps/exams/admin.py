from django.contrib import admin

from apps.exams.models import Exam, ExamSubject


class ExamSubjectInline(admin.TabularInline):
    model = ExamSubject
    extra = 0


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "academic_year", "start_date", "end_date", "deleted_at"]
    list_filter = ["academic_year"]
    search_fields = ["code", "name"]
    inlines = [ExamSubjectInline]


@admin.register(ExamSubject)
class ExamSubjectAdmin(admin.ModelAdmin):
    list_display = ["exam", "class_section", "subject", "max_marks"]
    list_filter = ["exam"]
