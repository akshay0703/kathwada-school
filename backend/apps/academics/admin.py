from django.contrib import admin

from apps.academics.models import (
    AcademicYear,
    ClassSection,
    ClassSectionSubject,
    SchoolClass,
    Section,
    Subject,
)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ["label", "school", "start_date", "end_date", "is_current", "deleted_at"]
    list_filter = ["school", "is_current"]
    search_fields = ["label", "school"]


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "deleted_at"]
    search_fields = ["name"]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["name", "deleted_at"]
    search_fields = ["name"]


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "deleted_at"]
    search_fields = ["name", "code"]


class ClassSectionSubjectInline(admin.TabularInline):
    model = ClassSectionSubject
    extra = 0


@admin.register(ClassSection)
class ClassSectionAdmin(admin.ModelAdmin):
    list_display = ["school_class", "section", "academic_year", "class_teacher", "deleted_at"]
    list_filter = ["academic_year", "school_class"]
    inlines = [ClassSectionSubjectInline]
