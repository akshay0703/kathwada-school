from rest_framework import viewsets

from apps.accounts.permissions import HasModulePermission
from apps.exams.models import Exam, ExamSubject
from apps.exams.serializers import ExamListSerializer, ExamSerializer, ExamSubjectSerializer

STANDARD_ACTION_MAP = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


class ExamViewSet(viewsets.ModelViewSet):
    """
    /api/v1/exams/ — permissions per the "Exams & Exam Components" matrix
    row: Admin VCEDX, Principal VCEX, Teacher V, Staff V, Student V,
    Parent V. Every role gets at least View; only Admin/Principal can
    Create/Edit/Delete. No row-level scoping needed here (unlike
    Marks/Attendance) since an Exam itself carries no per-student data —
    everyone who can see the module sees every exam in every academic year.
    """

    queryset = Exam.objects.select_related("academic_year").all()
    permission_classes = [HasModulePermission]
    module_key = "exams"
    permission_action_map = STANDARD_ACTION_MAP

    def get_serializer_class(self):
        if self.action == "list":
            return ExamListSerializer
        return ExamSerializer

    def get_queryset(self):
        qs = Exam.objects.select_related("academic_year").prefetch_related(
            "exam_subjects__class_section__school_class", "exam_subjects__class_section__section", "exam_subjects__subject"
        )
        academic_year_id = self.request.query_params.get("academic_year")
        if academic_year_id:
            qs = qs.filter(academic_year_id=academic_year_id)
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()


class ExamSubjectViewSet(viewsets.ModelViewSet):
    """
    /api/v1/exam-subjects/ — same "exams" module permissions, since
    configuring which subjects an exam covers (and their max marks) is
    part of exam management, not a separate module in the approved matrix.
    """

    queryset = ExamSubject.objects.select_related(
        "exam", "class_section__school_class", "class_section__section", "subject"
    ).all()
    serializer_class = ExamSubjectSerializer
    permission_classes = [HasModulePermission]
    module_key = "exams"
    permission_action_map = STANDARD_ACTION_MAP

    def get_queryset(self):
        qs = super().get_queryset()
        exam_id = self.request.query_params.get("exam")
        if exam_id:
            qs = qs.filter(exam_id=exam_id)
        class_section_id = self.request.query_params.get("class_section")
        if class_section_id:
            qs = qs.filter(class_section_id=class_section_id)
        return qs

    def perform_destroy(self, instance):
        # Pure configuration row — a real delete, same as ClassSectionSubject.
        instance.delete()
