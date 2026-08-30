import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, ClassSection, SchoolClass, Section
from apps.accounts.models import Module, PermissionAction, Role, RolePermission, User
from apps.people.models import Enrollment, Student

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
def students_module(db):
    return Module.objects.create(key="students", label="Students")


@pytest.fixture
def wire_permissions(db, roles, students_module):
    """Mirrors the real seeded matrix (apps/accounts/management/commands/seed_permissions.py)."""
    matrix = {
        "Admin": [V, C, E, D, X],
        "Principal": [V, C, E, X],
        "Teacher": [V],
        "Staff": [V, C, E, X],
        "Student": [V],
        "Parent": [V],
    }
    for role_name, actions in matrix.items():
        for action in actions:
            RolePermission.objects.create(role=roles[role_name], module=students_module, action=action)


def _user(role, email):
    return User.objects.create_user(email=email, password="StrongPass123!", role=role)


def _login(client, email):
    return client.post("/api/v1/auth/login/", {"email": email, "password": "StrongPass123!"}, format="json")


def _student_payload(**overrides):
    payload = {
        "admission_no": "KHS-2026-0001",
        "first_name": "Aarav",
        "last_name": "Patel",
        "dob": "2012-05-14",
        "gender": "male",
        "address": "Kathwada, Ahmedabad",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def class_section(db):
    academic_year = AcademicYear.objects.create(label="2026-27", start_date="2026-06-01", end_date="2027-04-30")
    school_class = SchoolClass.objects.create(name="Std 10", order=10)
    section = Section.objects.create(name="A")
    return ClassSection.objects.create(school_class=school_class, section=section, academic_year=academic_year)


@pytest.mark.django_db
class TestStudentPermissions:
    def test_admin_can_create_student(self, roles, wire_permissions):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/students/", _student_payload(), format="json")

        assert response.status_code == 201
        assert response.data["full_name"] == "Aarav Patel"

    def test_staff_can_create_student(self, roles, wire_permissions):
        _user(roles["Staff"], "staff@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "staff@example.com")

        response = client.post("/api/v1/students/", _student_payload(), format="json")

        assert response.status_code == 201

    def test_teacher_cannot_create_student(self, roles, wire_permissions):
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.post("/api/v1/students/", _student_payload(), format="json")

        assert response.status_code == 403

    def test_admission_no_unique(self, roles, wire_permissions):
        Student.objects.create(**_student_payload_model())
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/students/", _student_payload(first_name="Another"), format="json")

        assert response.status_code == 400

    def test_student_role_sees_only_own_record(self, roles, wire_permissions):
        own_user = _user(roles["Student"], "student@example.com")
        Student.objects.create(user=own_user, **_student_payload_model())
        Student.objects.create(**_student_payload_model(admission_no="KHS-2026-0002"))
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get("/api/v1/students/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["admission_no"] == "KHS-2026-0001"

    def test_parent_role_sees_no_students_yet(self, roles, wire_permissions):
        """Guardian/StudentGuardian doesn't exist yet — deny by default, not full access."""
        Student.objects.create(**_student_payload_model())
        _user(roles["Parent"], "parent@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/students/")

        assert response.status_code == 200
        assert response.data["count"] == 0

    def test_soft_delete_preserves_student_row(self, roles, wire_permissions):
        student = Student.objects.create(**_student_payload_model())
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/students/{student.id}/")

        assert response.status_code == 204
        assert Student.objects.filter(pk=student.pk).count() == 0
        assert Student.all_with_deleted.filter(pk=student.pk, deleted_at__isnull=False).count() == 1

    def test_search_by_name(self, roles, wire_permissions):
        Student.objects.create(**_student_payload_model())
        Student.objects.create(**_student_payload_model(admission_no="KHS-2026-0002", first_name="Diya", last_name="Shah"))
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get("/api/v1/students/?search=Diya")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["first_name"] == "Diya"


@pytest.mark.django_db
class TestEnrollment:
    def test_admin_can_enroll_student(self, roles, wire_permissions, class_section):
        student = Student.objects.create(**_student_payload_model())
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/enrollments/",
            {"student": student.id, "class_section": class_section.id, "roll_no": 1},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["roll_no"] == 1

    def test_duplicate_roll_no_in_class_section_rejected(self, roles, wire_permissions, class_section):
        student1 = Student.objects.create(**_student_payload_model())
        student2 = Student.objects.create(**_student_payload_model(admission_no="KHS-2026-0002"))
        Enrollment.objects.create(student=student1, class_section=class_section, roll_no=1)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/enrollments/",
            {"student": student2.id, "class_section": class_section.id, "roll_no": 1},
            format="json",
        )

        assert response.status_code == 400

    def test_same_student_cannot_double_enroll_same_class_section(self, roles, wire_permissions, class_section):
        student = Student.objects.create(**_student_payload_model())
        Enrollment.objects.create(student=student, class_section=class_section, roll_no=1)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/enrollments/",
            {"student": student.id, "class_section": class_section.id, "roll_no": 2},
            format="json",
        )

        assert response.status_code == 400

    def test_teacher_cannot_create_enrollment(self, roles, wire_permissions, class_section):
        student = Student.objects.create(**_student_payload_model())
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.post(
            "/api/v1/enrollments/",
            {"student": student.id, "class_section": class_section.id, "roll_no": 1},
            format="json",
        )

        assert response.status_code == 403

    def test_soft_delete_enrollment_preserves_row(self, roles, wire_permissions, class_section):
        student = Student.objects.create(**_student_payload_model())
        enrollment = Enrollment.objects.create(student=student, class_section=class_section, roll_no=1)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/enrollments/{enrollment.id}/")

        assert response.status_code == 204
        assert Enrollment.objects.filter(pk=enrollment.pk).count() == 0
        assert Enrollment.all_with_deleted.filter(pk=enrollment.pk, deleted_at__isnull=False).count() == 1

    def test_student_list_shows_current_class_section(self, roles, wire_permissions, class_section):
        student = Student.objects.create(**_student_payload_model())
        Enrollment.objects.create(student=student, class_section=class_section, roll_no=7)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get("/api/v1/students/")

        assert response.status_code == 200
        cs = response.data["results"][0]["current_class_section"]
        assert cs["roll_no"] == 7
        assert "Std 10-A" in cs["label"]


def _student_payload_model(**overrides):
    """Same shape as _student_payload() but for direct ORM .create() calls (no request payload wrapping)."""
    payload = _student_payload(**overrides)
    return payload
