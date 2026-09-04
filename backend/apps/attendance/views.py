from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.attendance.models import AttendanceRecord
from apps.attendance.serializers import AttendanceRecordSerializer, BulkMarkSerializer

STANDARD_ACTION_MAP = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    """
    /api/v1/attendance/ — permissions per the "Attendance" matrix row
    (docs/permissions.md / apps/accounts/management/commands/seed_permissions.py):
    Admin VCEDX, Principal VE, Teacher VCE (own classes only), Staff VC,
    Student V (own), Parent V (own child).

    Row-level scoping implemented now:
    - Teacher: queryset filtered to ClassSections they're actually assigned
      to via TeacherAssignment — this is the exact mechanism
      docs/permissions.md's "Scoping rules" section names for Attendance
      specifically ("a Teacher's queryset for Students/Marks/Attendance is
      filtered to ClassSections and Subjects they're actually assigned to").
    - Student: sees only their own records (via `student.user`).
    - Parent: sees only their linked children's records (via
      `StudentGuardian`, resolved by `guardian_child_student_ids()`).
    - Admin/Principal/Staff/superuser: full queryset.
    """

    queryset = AttendanceRecord.objects.select_related(
        "student", "class_section__school_class", "class_section__section", "class_section__academic_year", "marked_by"
    ).all()
    serializer_class = AttendanceRecordSerializer
    permission_classes = [HasModulePermission]
    module_key = "attendance"
    permission_action_map = {**STANDARD_ACTION_MAP, "bulk_mark": "create"}

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
                qs = qs.filter(class_section__in=_teacher_class_section_ids(user))
            elif role_name == "Student":
                qs = qs.filter(student__user=user)
            elif role_name == "Parent":
                qs = qs.filter(student_id__in=_guardian_child_student_ids(user))
            else:
                return qs.none()

        class_section_id = self.request.query_params.get("class_section")
        if class_section_id:
            qs = qs.filter(class_section_id=class_section_id)
        date_param = self.request.query_params.get("date")
        if date_param:
            qs = qs.filter(date=date_param)
        student_id = self.request.query_params.get("student")
        if student_id:
            qs = qs.filter(student_id=student_id)
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=False, methods=["post"], url_path="bulk-mark")
    def bulk_mark(self, request):
        """
        POST /api/v1/attendance/bulk-mark/
        body: {"class_section": <id>, "date": "YYYY-MM-DD",
               "records": [{"student": <id>, "status": "present"}, ...]}

        Marks (or corrects) attendance for a whole class-section on one
        date in a single request — every student listed must be actively
        enrolled in that class-section. Existing records for a
        (student, date) pair are updated in place rather than rejected,
        so re-submitting a corrected roster works the same way editing a
        single record does.
        """
        if not self.request.user.is_superuser:
            role_name = self.request.user.role.name if self.request.user.role else None
            if role_name == "Teacher":
                class_section_id = request.data.get("class_section")
                if class_section_id and int(class_section_id) not in _teacher_class_section_ids(self.request.user):
                    return Response(
                        {"class_section": ["You are not assigned to this class-section."]},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        serializer = BulkMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        records = serializer.save(marked_by=request.user)
        return Response(
            AttendanceRecordSerializer(records, many=True).data,
            status=status.HTTP_201_CREATED,
        )


def _teacher_class_section_ids(user):
    from apps.people.models import Teacher

    return set(
        Teacher.objects.filter(user=user).values_list(
            "assignments__class_section_subject__class_section_id", flat=True
        )
    )


def _guardian_child_student_ids(user):
    from apps.people.models import guardian_child_student_ids

    return guardian_child_student_ids(user)
