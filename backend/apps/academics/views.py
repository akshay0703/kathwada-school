from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.academics.models import (
    AcademicYear,
    ClassSection,
    ClassSectionSubject,
    SchoolClass,
    Section,
    Subject,
)
from apps.academics.serializers import (
    AcademicYearSerializer,
    ClassSectionSerializer,
    ClassSectionSubjectSerializer,
    SchoolClassSerializer,
    SectionSerializer,
    SubjectSerializer,
)
from apps.accounts.permissions import HasModulePermission

STANDARD_ACTION_MAP = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


class AcademicYearViewSet(viewsets.ModelViewSet):
    """
    /api/v1/academic-years/

    Permissions are entirely data-driven via HasModulePermission + the
    RolePermission table (see apps/accounts/permissions.py and
    apps/accounts/management/commands/seed_permissions.py) — this view
    itself contains no hardcoded role checks. Per the current seeded matrix:
    Admin has full access; Principal can view/create/edit/export but not
    delete; Teacher/Staff/Student/Parent can only view.
    """

    queryset = AcademicYear.objects.all().order_by("-start_date")
    serializer_class = AcademicYearSerializer
    permission_classes = [HasModulePermission]
    module_key = "academic_years"
    permission_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
        "mark_current": "edit",
    }

    def perform_destroy(self, instance):
        # Soft delete only — see AcademicYear's own docstring for why.
        # "Historical academic years must remain intact" is enforced here,
        # not just documented as a policy to remember.
        instance.soft_delete()

    @action(detail=True, methods=["post"], url_path="mark-current")
    def mark_current(self, request, pk=None):
        """
        POST /api/v1/academic-years/{id}/mark-current/
        Atomically unsets is_current on every other academic year for the
        same school, then sets it on this one — inside a single transaction,
        so there is never a moment with zero or two current years visible to
        a concurrent reader. The DB's partial unique constraint
        (academics_one_current_year_per_school) is the safety net if this
        code path is ever bypassed; this endpoint is the intended one.
        """
        year = self.get_object()
        with transaction.atomic():
            AcademicYear.objects.filter(school=year.school, is_current=True).exclude(pk=year.pk).update(
                is_current=False
            )
            year.is_current = True
            year.save(update_fields=["is_current"])
        return Response(AcademicYearSerializer(year).data)


class SchoolClassViewSet(viewsets.ModelViewSet):
    """/api/v1/classes/ — permissions per the "Classes / Sections" matrix row."""

    queryset = SchoolClass.objects.all().order_by("order", "name")
    serializer_class = SchoolClassSerializer
    permission_classes = [HasModulePermission]
    module_key = "classes_sections"
    permission_action_map = STANDARD_ACTION_MAP

    def perform_destroy(self, instance):
        instance.soft_delete()


class SectionViewSet(viewsets.ModelViewSet):
    """/api/v1/sections/ — permissions per the "Classes / Sections" matrix row."""

    queryset = Section.objects.all().order_by("name")
    serializer_class = SectionSerializer
    permission_classes = [HasModulePermission]
    module_key = "classes_sections"
    permission_action_map = STANDARD_ACTION_MAP

    def perform_destroy(self, instance):
        instance.soft_delete()


class SubjectViewSet(viewsets.ModelViewSet):
    """/api/v1/subjects/ — permissions per the "Subjects" matrix row."""

    queryset = Subject.objects.all().order_by("name")
    serializer_class = SubjectSerializer
    permission_classes = [HasModulePermission]
    module_key = "subjects"
    permission_action_map = STANDARD_ACTION_MAP

    def perform_destroy(self, instance):
        instance.soft_delete()


class ClassSectionViewSet(viewsets.ModelViewSet):
    """
    /api/v1/class-sections/ — the actual per-year offerings (e.g. "Std 10-A
    in 2026-27"). Permissions per the "Classes / Sections" matrix row, same
    module as SchoolClass/Section since a class-section is fundamentally
    part of class/section management, not a separate module.

    Subject assignment is exposed via two dedicated actions rather than
    allowing the `subjects` M2M through the main create/update payload —
    this mirrors AcademicYear's `mark-current` pattern (a deliberate,
    explicit action instead of an implicit side effect of a generic PATCH),
    and lets each assignment be validated/rejected independently (e.g.
    duplicate assignment) with a clear error rather than a bulk list either
    fully succeeding or failing.
    """

    queryset = ClassSection.objects.select_related("school_class", "section", "academic_year", "class_teacher").all()
    serializer_class = ClassSectionSerializer
    permission_classes = [HasModulePermission]
    module_key = "classes_sections"
    permission_action_map = {
        **STANDARD_ACTION_MAP,
        "add_subject": "edit",
        "remove_subject": "edit",
    }

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=True, methods=["post"], url_path="subjects")
    def add_subject(self, request, pk=None):
        """POST /api/v1/class-sections/{id}/subjects/  body: {"subject": <id>}"""
        class_section = self.get_object()
        subject_id = request.data.get("subject")
        if not subject_id:
            return Response({"subject": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            subject = Subject.objects.get(pk=subject_id)
        except Subject.DoesNotExist:
            return Response({"subject": ["Subject not found."]}, status=status.HTTP_400_BAD_REQUEST)

        if ClassSectionSubject.objects.filter(class_section=class_section, subject=subject).exists():
            return Response(
                {"non_field_errors": [f"'{subject.name}' is already assigned to this class-section."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        link = ClassSectionSubject.objects.create(class_section=class_section, subject=subject)
        return Response(ClassSectionSubjectSerializer(link).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="subjects/remove")
    def remove_subject(self, request, pk=None):
        """POST /api/v1/class-sections/{id}/subjects/remove/  body: {"subject": <id>}"""
        class_section = self.get_object()
        subject_id = request.data.get("subject")
        deleted, _ = ClassSectionSubject.objects.filter(
            class_section=class_section, subject_id=subject_id
        ).delete()
        if not deleted:
            return Response({"subject": ["This subject is not assigned to this class-section."]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
