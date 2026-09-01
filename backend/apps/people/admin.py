from django.contrib import admin

from apps.people.models import Enrollment, Student, Teacher, TeacherAssignment


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["admission_no", "first_name", "last_name", "dob", "gender", "deleted_at"]
    search_fields = ["admission_no", "first_name", "last_name"]
    list_filter = ["gender"]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "class_section", "roll_no", "status", "deleted_at"]
    list_filter = ["status", "class_section__academic_year"]
    search_fields = ["student__admission_no", "student__first_name", "student__last_name"]


class TeacherAssignmentInline(admin.TabularInline):
    model = TeacherAssignment
    extra = 0


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "phone", "email", "joined_date", "deleted_at"]
    search_fields = ["first_name", "last_name", "phone", "email"]
    inlines = [TeacherAssignmentInline]


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ["teacher", "class_section_subject"]
    search_fields = ["teacher__first_name", "teacher__last_name"]
