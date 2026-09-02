import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, ClassSection, SchoolClass, Section, Subject
from apps.accounts.models import Module, PermissionAction, Role, RolePermission, User
from apps.exams.models import Exam, ExamSubject

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
def exams_module(db):
    return Module.objects.create(key="exams", label="Exams")


@pytest.fixture
def wire_permissions(db, roles, exams_module):
    """Mirrors the real seeded matrix (apps/accounts/management/commands/seed_permissions.py)."""
    matrix = {
        "Admin": [V, C, E, D, X],
        "Principal": [V, C, E, X],
        "Teacher": [V],
        "Staff": [V],
        "Student": [V],
        "Parent": [V],
    }
    for role_name, actions in matrix.items():
        for action in actions:
            RolePermission.objects.create(role=roles[role_name], module=exams_module, action=action)


def _user(role, email):
    return User.objects.create_user(email=email, password="StrongPass123!", role=role)


def _login(client, email):
    return client.post("/api/v1/auth/login/", {"email": email, "password": "StrongPass123!"}, format="json")


@pytest.fixture
def academic_year(db):
    return AcademicYear.objects.create(label="2026-27", start_date="2026-06-01", end_date="2027-04-30")


@pytest.fixture
def class_section(db, academic_year):
    school_class = SchoolClass.objects.create(name="Std 10", order=10)
    section = Section.objects.create(name="A")
    return ClassSection.objects.create(school_class=school_class, section=section, academic_year=academic_year)


@pytest.mark.django_db
class TestExamPermissions:
    def test_admin_can_create_exam(self, roles, wire_permissions, academic_year):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/exams/",
            {"academic_year": academic_year.id, "code": "UT1", "name": "Unit Test 1", "start_date": "2026-08-01", "end_date": "2026-08-05"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["code"] == "UT1"

    def test_teacher_cannot_create_exam(self, roles, wire_permissions, academic_year):
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.post(
            "/api/v1/exams/",
            {"academic_year": academic_year.id, "code": "UT1", "name": "Unit Test 1", "start_date": "2026-08-01", "end_date": "2026-08-05"},
            format="json",
        )

        assert response.status_code == 403

    def test_student_can_view_exams(self, roles, wire_permissions, academic_year):
        Exam.objects.create(academic_year=academic_year, code="UT1", name="Unit Test 1", start_date="2026-08-01", end_date="2026-08-05")
        _user(roles["Student"], "student@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get("/api/v1/exams/")

        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_duplicate_code_per_year_rejected(self, roles, wire_permissions, academic_year):
        Exam.objects.create(academic_year=academic_year, code="UT1", name="Unit Test 1", start_date="2026-08-01", end_date="2026-08-05")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/exams/",
            {"academic_year": academic_year.id, "code": "UT1", "name": "Unit Test 1 Retake", "start_date": "2026-09-01", "end_date": "2026-09-05"},
            format="json",
        )

        assert response.status_code == 400

    def test_end_date_before_start_date_rejected(self, roles, wire_permissions, academic_year):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/exams/",
            {"academic_year": academic_year.id, "code": "UT1", "name": "Unit Test 1", "start_date": "2026-08-05", "end_date": "2026-08-01"},
            format="json",
        )

        assert response.status_code == 400

    def test_soft_delete_preserves_exam_row(self, roles, wire_permissions, academic_year):
        exam = Exam.objects.create(academic_year=academic_year, code="UT1", name="Unit Test 1", start_date="2026-08-01", end_date="2026-08-05")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/exams/{exam.id}/")

        assert response.status_code == 204
        assert Exam.objects.filter(pk=exam.pk).count() == 0
        assert Exam.all_with_deleted.filter(pk=exam.pk, deleted_at__isnull=False).count() == 1


@pytest.mark.django_db
class TestExamSubject:
    def test_admin_can_configure_exam_subject(self, roles, wire_permissions, academic_year, class_section):
        exam = Exam.objects.create(academic_year=academic_year, code="UT1", name="Unit Test 1", start_date="2026-08-01", end_date="2026-08-05")
        subject = Subject.objects.create(name="Mathematics", code="MATH")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/exam-subjects/",
            {"exam": exam.id, "class_section": class_section.id, "subject": subject.id, "max_marks": "50.00"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["subject_code"] == "MATH"

    def test_duplicate_exam_subject_rejected(self, roles, wire_permissions, academic_year, class_section):
        exam = Exam.objects.create(academic_year=academic_year, code="UT1", name="Unit Test 1", start_date="2026-08-01", end_date="2026-08-05")
        subject = Subject.objects.create(name="Mathematics", code="MATH")
        ExamSubject.objects.create(exam=exam, class_section=class_section, subject=subject, max_marks=50)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/exam-subjects/",
            {"exam": exam.id, "class_section": class_section.id, "subject": subject.id, "max_marks": "60.00"},
            format="json",
        )

        assert response.status_code == 400
