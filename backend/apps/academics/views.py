from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.academics.models import AcademicYear
from apps.academics.serializers import AcademicYearSerializer
from apps.accounts.permissions import HasModulePermission


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
