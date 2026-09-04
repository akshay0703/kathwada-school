from rest_framework import viewsets

from apps.accounts.permissions import HasModulePermission
from apps.fees.models import FeeInvoice, FeePayment, FeeStructure
from apps.fees.serializers import (
    FeeInvoiceListSerializer,
    FeeInvoiceSerializer,
    FeePaymentSerializer,
    FeeStructureSerializer,
)

STANDARD_ACTION_MAP = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


def _scope_by_role(qs, user, student_field):
    """
    Shared row-level scoping for FeeInvoice/FeePayment, matching the "Fees"
    matrix row (docs/permissions.md / seed_permissions.py): Admin/Staff/
    Principal see everything (their Create/Edit/Delete rights differ, but
    that's enforced by HasModulePermission, not queryset scoping); Teacher
    gets zero RolePermission rows on this module at all, so they 403 before
    ever reaching here; Student sees only their own; Parent sees only
    their linked children's (via `StudentGuardian`, resolved by
    `guardian_child_student_ids()`).
    """
    if not user or not user.is_authenticated:
        return qs.none()
    if user.is_superuser:
        return qs
    role_name = user.role.name if user.role else None
    if role_name in ("Admin", "Principal", "Staff"):
        return qs
    if role_name == "Student":
        return qs.filter(**{f"{student_field}__user": user})
    if role_name == "Parent":
        from apps.people.models import guardian_child_student_ids

        return qs.filter(**{f"{student_field}_id__in": guardian_child_student_ids(user)})
    return qs.none()


class FeeStructureViewSet(viewsets.ModelViewSet):
    """
    /api/v1/fee-structures/ — permissions per the "Fees" matrix row: Admin
    VCEDX, Principal VX (view + export only), Teacher none at all, Staff
    VCEX, Student V, Parent V. No personal data lives on FeeStructure
    itself (it's a per-class-section fee schedule, not a per-student bill),
    so no row-level scoping is needed beyond the module gate itself.
    """

    queryset = FeeStructure.objects.select_related("class_section__school_class", "class_section__section", "academic_year").all()
    serializer_class = FeeStructureSerializer
    permission_classes = [HasModulePermission]
    module_key = "fees"
    permission_action_map = STANDARD_ACTION_MAP

    def get_queryset(self):
        qs = super().get_queryset()
        class_section_id = self.request.query_params.get("class_section")
        if class_section_id:
            qs = qs.filter(class_section_id=class_section_id)
        academic_year_id = self.request.query_params.get("academic_year")
        if academic_year_id:
            qs = qs.filter(academic_year_id=academic_year_id)
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()


class FeeInvoiceViewSet(viewsets.ModelViewSet):
    """
    /api/v1/fee-invoices/ — same "Fees" module permissions as
    FeeStructure. Row-level scoping via `_scope_by_role` (Student: own
    invoices only).
    """

    queryset = FeeInvoice.objects.select_related(
        "student", "fee_structure__class_section__school_class", "fee_structure__class_section__section", "fee_structure__academic_year"
    ).prefetch_related("payments")
    permission_classes = [HasModulePermission]
    module_key = "fees"
    permission_action_map = STANDARD_ACTION_MAP

    def get_serializer_class(self):
        if self.action == "list":
            return FeeInvoiceListSerializer
        return FeeInvoiceSerializer

    def get_queryset(self):
        qs = _scope_by_role(FeeInvoiceViewSet.queryset, self.request.user, "student")
        student_id = self.request.query_params.get("student")
        if student_id:
            qs = qs.filter(student_id=student_id)
        fee_structure_id = self.request.query_params.get("fee_structure")
        if fee_structure_id:
            qs = qs.filter(fee_structure_id=fee_structure_id)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()


class FeePaymentViewSet(viewsets.ModelViewSet):
    """
    /api/v1/fee-payments/ — same "Fees" module permissions. Row-level
    scoping via `_scope_by_role` (Student: payments on their own invoices
    only). Recomputes the parent invoice's status after every soft-delete
    (create/update already do this in FeePaymentSerializer).
    """

    queryset = FeePayment.objects.select_related("fee_invoice__student", "recorded_by")
    serializer_class = FeePaymentSerializer
    permission_classes = [HasModulePermission]
    module_key = "fees"
    permission_action_map = STANDARD_ACTION_MAP

    def get_queryset(self):
        qs = _scope_by_role(FeePaymentViewSet.queryset, self.request.user, "fee_invoice__student")
        fee_invoice_id = self.request.query_params.get("fee_invoice")
        if fee_invoice_id:
            qs = qs.filter(fee_invoice_id=fee_invoice_id)
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()
        instance.fee_invoice.recompute_status()
