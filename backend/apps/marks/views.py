from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.marks.models import Mark
from apps.marks.serializers import BulkMarkSaveSerializer, MarkSerializer

STANDARD_ACTION_MAP = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


class MarkViewSet(viewsets.ModelViewSet):
    """
    /api/v1/marks/ — permissions per the "Marks Entry" matrix row: Admin
    VCEDX, Principal VE (no Create), Teacher VCE (own assigned
    subjects/classes only), Staff none at all, Student V (own), Parent V
    (own child).

    Row-level scoping implemented now, same mechanism/pattern as
    Attendance:
    - Teacher: queryset filtered to ClassSections they're assigned to via
      TeacherAssignment (docs/permissions.md names Marks explicitly for
      this exact scoping rule).
    - Student: sees only their own marks (via `student.user`).
    - Admin/Principal/superuser: full queryset. Staff: no RolePermission
      rows on this module at all, so they 403 before reaching get_queryset.

    Deliberately NOT yet implemented (documented, not silently skipped):
    - Parent "V (own child)" needs `StudentGuardian`, which doesn't exist
      yet — Parents get an empty queryset rather than an error.
    - No draft->publish gate: checked directly against
      apps/accounts/management/commands/seed_permissions.py, the "marks"
      module row has no PUBLISH action at all (only report_cards/
      website_cms do), so Student/Parent's View is unconditional once
      scoped to their own record.
    """

    queryset = Mark.objects.select_related(
        "student", "exam_subject__exam", "exam_subject__subject", "exam_subject__class_section", "entered_by"
    ).all()
    serializer_class = MarkSerializer
    permission_classes = [HasModulePermission]
    module_key = "marks"
    permission_action_map = {**STANDARD_ACTION_MAP, "bulk_save": "create"}

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if not user.is_superuser:
            role_name = user.role.name if user.role else None
            if role_name in ("Admin", "Principal"):
                pass
            elif role_name == "Teacher":
                qs = qs.filter(exam_subject__class_section__in=_teacher_class_section_ids(user))
            elif role_name == "Student":
                qs = qs.filter(student__user=user)
            else:
                # Staff (no rows on this module) / Parent (StudentGuardian
                # doesn't exist yet): deny by default.
                return qs.none()

        exam_subject_id = self.request.query_params.get("exam_subject")
        if exam_subject_id:
            qs = qs.filter(exam_subject_id=exam_subject_id)
        exam_id = self.request.query_params.get("exam")
        if exam_id:
            qs = qs.filter(exam_subject__exam_id=exam_id)
        student_id = self.request.query_params.get("student")
        if student_id:
            qs = qs.filter(student_id=student_id)
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=False, methods=["post"], url_path="bulk-save")
    def bulk_save(self, request):
        """
        POST /api/v1/marks/bulk-save/
        body: {"exam_subject": <id>, "records": [{"student": <id>,
               "marks_obtained": 78}, ...]}

        Saves (or corrects) marks for a whole class-section/subject/exam
        combination in one request — every student listed must be actively
        enrolled in that exam_subject's class-section, and no mark may
        exceed that exam_subject's max_marks. Existing marks are updated in
        place, so re-submitting a corrected sheet works the same way
        editing a single mark does.
        """
        if not self.request.user.is_superuser:
            role_name = self.request.user.role.name if self.request.user.role else None
            if role_name == "Teacher":
                exam_subject_id = request.data.get("exam_subject")
                exam_subject_class_section_id = _class_section_id_for_exam_subject(exam_subject_id)
                if exam_subject_class_section_id is not None and exam_subject_class_section_id not in _teacher_class_section_ids(
                    self.request.user
                ):
                    return Response(
                        {"exam_subject": ["You are not assigned to this class-section."]},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        serializer = BulkMarkSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        records = serializer.save(entered_by=request.user)
        return Response(MarkSerializer(records, many=True).data, status=status.HTTP_201_CREATED)


def _teacher_class_section_ids(user):
    from apps.people.models import Teacher

    return set(
        Teacher.objects.filter(user=user).values_list(
            "assignments__class_section_subject__class_section_id", flat=True
        )
    )


def _class_section_id_for_exam_subject(exam_subject_id):
    from apps.exams.models import ExamSubject

    if not exam_subject_id:
        return None
    return ExamSubject.objects.filter(pk=exam_subject_id).values_list("class_section_id", flat=True).first()
