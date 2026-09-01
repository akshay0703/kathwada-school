from rest_framework import filters, viewsets

from apps.accounts.permissions import HasModulePermission
from apps.people.models import Enrollment, Student, Teacher, TeacherAssignment
from apps.people.serializers import (
    EnrollmentSerializer,
    StudentListSerializer,
    StudentSerializer,
    TeacherAssignmentSerializer,
    TeacherListSerializer,
    TeacherSerializer,
)

STANDARD_ACTION_MAP = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


class StudentViewSet(viewsets.ModelViewSet):
    """
    /api/v1/students/ — permissions per the "Students" matrix row
    (docs/permissions.md): Admin VCEDX, Principal VCEX, Staff VCEX,
    Teacher/Student/Parent View-only (with row-level scoping below).

    Row-level scoping implemented now:
    - Student role: sees only their own record (via `user`).
    - Admin/Principal/Staff/superuser: full queryset.

    Row-level scoping deliberately NOT yet implemented (documented, not
    silently skipped):
    - Teacher "V (own class only)" needs a `TeacherAssignment` table, which
      doesn't exist yet (Teacher module is a later milestone per
      instruction) — Teachers currently see the full list once granted View
      by the RolePermission table, same interim state as Academic Years'
      Teacher row before scoping existed.
    - Parent "V (own children)" needs `StudentGuardian`, which also doesn't
      exist yet (Guardian module is a later milestone) — Parents currently
      see an empty queryset rather than an error, since granting them
      results with no ownership check would be a real data leak.
    """

    queryset = Student.objects.all().order_by("admission_no")
    permission_classes = [HasModulePermission]
    module_key = "students"
    permission_action_map = STANDARD_ACTION_MAP
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["admission_no", "first_name", "last_name", "phone"]
    ordering_fields = ["admission_no", "first_name", "last_name", "dob", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return StudentListSerializer
        return StudentSerializer

    def get_queryset(self):
        qs = Student.objects.all().prefetch_related(
            "enrollments__class_section__school_class",
            "enrollments__class_section__section",
            "enrollments__class_section__academic_year",
        )
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if user.is_superuser:
            pass
        else:
            role_name = user.role.name if user.role else None
            if role_name in ("Admin", "Principal", "Staff", "Teacher"):
                pass
            elif role_name == "Student":
                qs = qs.filter(user=user)
            else:
                # Parent (or no role): StudentGuardian doesn't exist yet —
                # deny by default rather than silently returning everything.
                return qs.none()

        # Manual, dependency-free filtering (no django-filter installed):
        gender = self.request.query_params.get("gender")
        if gender:
            qs = qs.filter(gender=gender)
        class_section_id = self.request.query_params.get("class_section")
        if class_section_id:
            qs = qs.filter(enrollments__class_section_id=class_section_id, enrollments__status="active")
        return qs.distinct()

    def perform_destroy(self, instance):
        instance.soft_delete()


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    /api/v1/enrollments/ — same "Students" module permissions, since
    enrolling/promoting a student is part of student management, not a
    separate module in the approved matrix.
    """

    queryset = Enrollment.objects.select_related(
        "student", "class_section__school_class", "class_section__section", "class_section__academic_year"
    ).all()
    serializer_class = EnrollmentSerializer
    permission_classes = [HasModulePermission]
    module_key = "students"
    permission_action_map = STANDARD_ACTION_MAP

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if not user.is_superuser:
            role_name = user.role.name if user.role else None
            if role_name in ("Admin", "Principal", "Staff", "Teacher"):
                pass
            elif role_name == "Student":
                qs = qs.filter(student__user=user)
            else:
                return qs.none()

        class_section_id = self.request.query_params.get("class_section")
        if class_section_id:
            qs = qs.filter(class_section_id=class_section_id)
        student_id = self.request.query_params.get("student")
        if student_id:
            qs = qs.filter(student_id=student_id)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()


class TeacherViewSet(viewsets.ModelViewSet):
    """
    /api/v1/teachers/ — permissions per the "Teachers" matrix row
    (docs/prototype-analysis.md §3): Admin VCEDX, Principal VEX, Staff V,
    Teacher V(own record)+E(own record — field-level restriction to "own
    contact info only" is not enforced yet, same kind of documented gap as
    Student's row-level scoping), Student/Parent no access at all (no
    RolePermission rows for those roles on this module, so they 403 before
    ever reaching get_queryset).
    """

    queryset = Teacher.objects.all().order_by("first_name", "last_name")
    permission_classes = [HasModulePermission]
    module_key = "teachers"
    permission_action_map = STANDARD_ACTION_MAP
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name", "phone", "email"]
    ordering_fields = ["first_name", "last_name", "joined_date", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return TeacherListSerializer
        return TeacherSerializer

    def get_queryset(self):
        qs = Teacher.objects.all().prefetch_related(
            "assignments__class_section_subject__subject",
            "assignments__class_section_subject__class_section__school_class",
            "assignments__class_section_subject__class_section__section",
            "assignments__class_section_subject__class_section__academic_year",
        )
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if not user.is_superuser:
            role_name = user.role.name if user.role else None
            if role_name in ("Admin", "Principal", "Staff"):
                pass
            elif role_name == "Teacher":
                qs = qs.filter(user=user)
            else:
                # Student/Parent: no RolePermission rows exist for this
                # module at all per the matrix, so this branch is a
                # deny-by-default backstop, not the primary gate.
                return qs.none()

        class_section_id = self.request.query_params.get("class_section")
        if class_section_id:
            qs = qs.filter(assignments__class_section_subject__class_section_id=class_section_id)
        return qs.distinct()

    def perform_destroy(self, instance):
        instance.soft_delete()


class TeacherAssignmentViewSet(viewsets.ModelViewSet):
    """
    /api/v1/teacher-assignments/ — same "Teachers" module permissions,
    since assigning a teacher to a class-section subject is part of teacher
    management, not a separate module in the approved matrix (mirrors how
    Enrollment reuses the "students" module_key).
    """

    queryset = TeacherAssignment.objects.select_related(
        "teacher",
        "class_section_subject__subject",
        "class_section_subject__class_section__school_class",
        "class_section_subject__class_section__section",
        "class_section_subject__class_section__academic_year",
    ).all()
    serializer_class = TeacherAssignmentSerializer
    permission_classes = [HasModulePermission]
    module_key = "teachers"
    permission_action_map = STANDARD_ACTION_MAP

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if not user.is_superuser:
            role_name = user.role.name if user.role else None
            if role_name in ("Admin", "Principal", "Staff"):
                pass
            elif role_name == "Teacher":
                qs = qs.filter(teacher__user=user)
            else:
                return qs.none()

        teacher_id = self.request.query_params.get("teacher")
        if teacher_id:
            qs = qs.filter(teacher_id=teacher_id)
        class_section_subject_id = self.request.query_params.get("class_section_subject")
        if class_section_subject_id:
            qs = qs.filter(class_section_subject_id=class_section_subject_id)
        return qs

    def perform_destroy(self, instance):
        # Pure association row — a real delete, not a soft delete, same as
        # ClassSectionSubject (see TeacherAssignment's model docstring).
        instance.delete()
