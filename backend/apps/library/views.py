from datetime import date

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.library.models import Book, BookIssue
from apps.library.serializers import BookIssueSerializer, BookSerializer

STANDARD_ACTION_MAP = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


class BookViewSet(viewsets.ModelViewSet):
    """
    /api/v1/books/ — permissions per the "Library" matrix row: Admin
    VCEDX, Principal VX (view + export only), Teacher V, Staff VCEDX,
    Student V, Parent V. No personal data lives on Book itself, so no
    row-level scoping is needed beyond the module gate.

    Note: the matrix's intent for Teacher's Create right is "issue/return"
    (BookIssue), not catalog management — but RolePermission is
    module-level, not per-ViewSet (the same flat granularity already true
    of, e.g., Enrollment sharing Student's module permissions), so a
    Teacher granted Create on "library" can also create Book rows here.
    Splitting permission granularity finer than module-level would be a
    redesign of the permission system itself, out of scope for this batch.
    """

    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [HasModulePermission]
    module_key = "library"
    permission_action_map = STANDARD_ACTION_MAP

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(title__icontains=search)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()


class BookIssueViewSet(viewsets.ModelViewSet):
    """
    /api/v1/book-issues/ — same "Library" module permissions as Book.
    Teacher's "C (issue/return)" right is deliberately routed through
    `create` (the normal POST for issuing) and the dedicated `return_book`
    action below (also mapped to `create`, not `edit`) — Teachers have no
    Edit/Delete on this module at all, so a generic PATCH is correctly
    denied for them; returning a book is modeled as its own explicit
    action instead, the same "explicit action rather than an implicit side
    effect of a generic PATCH" pattern already used by AcademicYear's
    mark-current and ClassSection's subject assignment actions.

    Row-level scoping:
    - Student: sees only their own loans (via `student.user`).
    - Parent: sees only their linked children's loans (via
      `StudentGuardian`, resolved by `guardian_child_student_ids()`).
    - Admin/Principal/Staff/Teacher/superuser: full queryset.
    """

    queryset = BookIssue.objects.select_related("book", "student").all()
    serializer_class = BookIssueSerializer
    permission_classes = [HasModulePermission]
    module_key = "library"
    permission_action_map = {**STANDARD_ACTION_MAP, "return_book": "create"}

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
            elif role_name == "Parent":
                from apps.people.models import guardian_child_student_ids

                qs = qs.filter(student_id__in=guardian_child_student_ids(user))
            else:
                return qs.none()

        book_id = self.request.query_params.get("book")
        if book_id:
            qs = qs.filter(book_id=book_id)
        student_id = self.request.query_params.get("student")
        if student_id:
            qs = qs.filter(student_id=student_id)
        outstanding = self.request.query_params.get("outstanding")
        if outstanding == "true":
            qs = qs.filter(return_date__isnull=True)
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=True, methods=["post"], url_path="return")
    def return_book(self, request, pk=None):
        """POST /api/v1/book-issues/{id}/return/ — marks this loan returned today (or on an explicitly given date), computing any overdue fine."""
        issue = self.get_object()
        if issue.return_date:
            return Response({"detail": "This book has already been returned."}, status=status.HTTP_400_BAD_REQUEST)
        return_date = request.data.get("return_date") or date.today().isoformat()
        issue.return_date = return_date
        issue.save()
        return Response(BookIssueSerializer(issue).data)
