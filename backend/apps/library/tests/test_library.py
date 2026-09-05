import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Module, PermissionAction, Role, RolePermission, User
from apps.library.models import Book, BookIssue
from apps.people.models import Guardian, Student, StudentGuardian

V, C, E, D, X = (
    PermissionAction.VIEW,
    PermissionAction.CREATE,
    PermissionAction.EDIT,
    PermissionAction.DELETE,
    PermissionAction.EXPORT,
)


@pytest.fixture
def roles(db):
    return {
        name: Role.objects.create(name=name)
        for name in ["Admin", "Principal", "Teacher", "Staff", "Student", "Parent"]
    }


@pytest.fixture
def library_module(db):
    return Module.objects.create(key="library", label="Library")


@pytest.fixture
def wire_permissions(db, roles, library_module):
    """Mirrors the real seeded matrix (apps/accounts/management/commands/seed_permissions.py)."""
    matrix = {
        "Admin": [V, C, E, D, X],
        "Principal": [V, X],
        "Teacher": [V, C],
        "Staff": [V, C, E, D, X],
        "Student": [V],
        "Parent": [V],
    }
    for role_name, actions in matrix.items():
        for action in actions:
            RolePermission.objects.create(role=roles[role_name], module=library_module, action=action)


def _user(role, email):
    return User.objects.create_user(email=email, password="StrongPass123!", role=role)


def _login(client, email):
    return client.post("/api/v1/auth/login/", {"email": email, "password": "StrongPass123!"}, format="json")


@pytest.fixture
def book(db):
    return Book.objects.create(title="A Tale of Two Cities", author="Charles Dickens", category="Fiction", total_copies=2)


@pytest.fixture
def student(db):
    return Student.objects.create(admission_no="KHS-2026-0001", first_name="Aarav", last_name="Patel", dob="2012-05-14")


@pytest.fixture
def other_student(db):
    return Student.objects.create(admission_no="KHS-2026-0002", first_name="Diya", last_name="Shah", dob="2012-01-01")


@pytest.mark.django_db
class TestBookPermissions:
    def test_admin_can_create_book(self, roles, wire_permissions):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/books/", {"title": "1984", "author": "George Orwell", "category": "Fiction", "total_copies": 3}, format="json"
        )

        assert response.status_code == 201
        assert response.data["available_copies"] == 3

    def test_teacher_can_create_book(self, roles, wire_permissions):
        """
        Library matrix row: Teacher has V,C. The docs' intent for Teacher's
        C is "issue/return", not catalog management — but this codebase's
        RolePermission table is module-level, not per-ViewSet (the same
        flat-granularity reality as Enrollment sharing Student's module
        permissions), so Teacher's C on "library" necessarily also grants
        Book creation. Documented here rather than worked around, since
        splitting permission granularity finer than module-level would be
        a redesign of the permission system itself, out of scope for this
        batch.
        """
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.post("/api/v1/books/", {"title": "1984", "total_copies": 1}, format="json")

        assert response.status_code == 201

    def test_staff_role_without_grant_cannot_create_book(self, roles, wire_permissions):
        """Sanity check on the negative path: a role genuinely missing Create is denied."""
        _user(roles["Student"], "student@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.post("/api/v1/books/", {"title": "1984", "total_copies": 1}, format="json")

        assert response.status_code == 403

    def test_student_can_view_books(self, roles, wire_permissions, book):
        _user(roles["Student"], "student@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get("/api/v1/books/")

        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_soft_delete_preserves_book_row(self, roles, wire_permissions, book):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/books/{book.id}/")

        assert response.status_code == 204
        assert Book.objects.filter(pk=book.pk).count() == 0
        assert Book.all_with_deleted.filter(pk=book.pk, deleted_at__isnull=False).count() == 1


@pytest.mark.django_db
class TestBookIssueWorkflow:
    def test_teacher_can_issue_book(self, roles, wire_permissions, book, student):
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.post(
            "/api/v1/book-issues/", {"book": book.id, "student": student.id, "issue_date": "2026-07-01"}, format="json"
        )

        assert response.status_code == 201
        assert response.data["due_date"] == "2026-07-15"  # default 14-day loan period
        assert response.data["fine_amount"] == "0.00"

    def test_cannot_issue_when_no_copies_available(self, roles, wire_permissions, student, other_student):
        single_copy_book = Book.objects.create(title="Rare Book", total_copies=1)
        BookIssue.objects.create(book=single_copy_book, student=student, issue_date="2026-07-01", due_date="2026-07-15")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/book-issues/", {"book": single_copy_book.id, "student": other_student.id, "issue_date": "2026-07-02"}, format="json"
        )

        assert response.status_code == 400
        assert "book" in response.data

    def test_cannot_double_issue_same_book_to_same_student(self, roles, wire_permissions, book, student):
        BookIssue.objects.create(book=book, student=student, issue_date="2026-07-01", due_date="2026-07-15")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/book-issues/", {"book": book.id, "student": student.id, "issue_date": "2026-07-05"}, format="json"
        )

        assert response.status_code == 400

    def test_available_copies_decreases_after_issue(self, roles, wire_permissions, book, student):
        assert book.available_copies() == 2
        BookIssue.objects.create(book=book, student=student, issue_date="2026-07-01", due_date="2026-07-15")

        assert book.available_copies() == 1

    def test_return_book_on_time_has_no_fine(self, roles, wire_permissions, book, student):
        issue = BookIssue.objects.create(book=book, student=student, issue_date="2026-07-01", due_date="2026-07-15")
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.post(f"/api/v1/book-issues/{issue.id}/return/", {"return_date": "2026-07-10"}, format="json")

        assert response.status_code == 200
        assert response.data["return_date"] == "2026-07-10"
        assert response.data["fine_amount"] == "0.00"

    def test_return_book_overdue_computes_fine(self, roles, wire_permissions, book, student):
        issue = BookIssue.objects.create(book=book, student=student, issue_date="2026-07-01", due_date="2026-07-15")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(f"/api/v1/book-issues/{issue.id}/return/", {"return_date": "2026-07-20"}, format="json")

        assert response.status_code == 200
        assert response.data["fine_amount"] == "10.00"  # 5 days overdue * 2.00/day

    def test_cannot_return_already_returned_book(self, roles, wire_permissions, book, student):
        issue = BookIssue.objects.create(book=book, student=student, issue_date="2026-07-01", due_date="2026-07-15", return_date="2026-07-10")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(f"/api/v1/book-issues/{issue.id}/return/", {}, format="json")

        assert response.status_code == 400

    def test_returned_copy_becomes_available_again(self, roles, wire_permissions, book, student):
        issue = BookIssue.objects.create(book=book, student=student, issue_date="2026-07-01", due_date="2026-07-15")
        assert book.available_copies() == 1
        issue.return_date = "2026-07-10"
        issue.save()

        assert book.available_copies() == 2

    def test_student_sees_only_own_issues(self, roles, wire_permissions, book, student, other_student):
        own_user = _user(roles["Student"], "student@example.com")
        student.user = own_user
        student.save()
        BookIssue.objects.create(book=book, student=student, issue_date="2026-07-01", due_date="2026-07-15")
        BookIssue.objects.create(book=book, student=other_student, issue_date="2026-07-01", due_date="2026-07-15")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get("/api/v1/book-issues/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["student"] == student.id

    def test_parent_sees_only_linked_child_issues(self, roles, wire_permissions, book, student, other_student):
        parent_user = _user(roles["Parent"], "parent@example.com")
        guardian = Guardian.objects.create(user=parent_user, name="Rakesh Patel", relationship="father")
        StudentGuardian.objects.create(student=student, guardian=guardian)
        BookIssue.objects.create(book=book, student=student, issue_date="2026-07-01", due_date="2026-07-15")
        BookIssue.objects.create(book=book, student=other_student, issue_date="2026-07-01", due_date="2026-07-15")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/book-issues/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["student"] == student.id

    def test_soft_delete_preserves_issue_row(self, roles, wire_permissions, book, student):
        issue = BookIssue.objects.create(book=book, student=student, issue_date="2026-07-01", due_date="2026-07-15")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/book-issues/{issue.id}/")

        assert response.status_code == 204
        assert BookIssue.objects.filter(pk=issue.pk).count() == 0
        assert BookIssue.all_with_deleted.filter(pk=issue.pk, deleted_at__isnull=False).count() == 1
