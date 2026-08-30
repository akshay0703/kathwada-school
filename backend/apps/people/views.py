from rest_framework import filters, viewsets

from apps.accounts.permissions import HasModulePermission
from apps.people.models import Enrollment, Student
from apps.people.serializers import EnrollmentSerializer, StudentListSerializer, StudentSerializer

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
