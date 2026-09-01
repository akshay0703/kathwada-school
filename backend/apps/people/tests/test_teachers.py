import pytest
from rest_framework.test import APIClient

from apps.academics.models import (
    AcademicYear,
    ClassSection,
    ClassSectionSubject,
    SchoolClass,
    Section,
    Subject,
)
from apps.accounts.models import Module, PermissionAction, Role, RolePermission, User
from apps.people.models import Teacher, TeacherAssignment

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
def teachers_module(db):
    return Module.objects.create(key="teachers", label="Teachers")


@pytest.fixture
def wire_permissions(db, roles, teachers_module):
    """Mirrors the real seeded matrix (apps/accounts/management/commands/seed_permissions.py)."""
    matrix = {
        "Admin": [V, C, E, D, X],
        "Principal": [V, E, X],
        "Teacher": [V, E],
        "Staff": [V],
        # Student/Parent intentionally get no rows at all — matches
        # prototype-analysis.md's "Teachers" row: "— | —" for those roles.
    }
    for role_name, actions in matrix.items():
        for action in actions:
            RolePermission.objects.create(role=roles[role_name], module=teachers_module, action=action)


def _user(role, email):
    return User.objects.create_user(email=email, password="StrongPass123!", role=role)


def _login(client, email):
    return client.post("/api/v1/auth/login/", {"email": email, "password": "StrongPass123!"}, format="json")


def _teacher_payload(**overrides):
    payload = {
        "first_name": "Meera",
        "last_name": "Joshi",
        "phone": "9876543210",
        "email": "meera.joshi@example.com",
        "joined_date": "2020-06-01",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def class_section_subject(db):
    academic_year = AcademicYear.objects.create(label="2026-27", start_date="2026-06-01", end_date="2027-04-30")
    school_class = SchoolClass.objects.create(name="Std 10", order=10)
    section = Section.objects.create(name="A")
    class_section = ClassSection.objects.create(school_class=school_class, section=section, academic_year=academic_year)
    subject = Subject.objects.create(name="Mathematics", code="MATH")
    return ClassSectionSubject.objects.create(class_section=class_section, subject=subject)


@pytest.mark.django_db
class TestTeacherPermissions:
    def test_admin_can_create_teacher(self, roles, wire_permissions):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/teachers/", _teacher_payload(), format="json")

        assert response.status_code == 201
        assert response.data["full_name"] == "Meera Joshi"

    def test_principal_cannot_create_teacher(self, roles, wire_permissions):
        """Teachers matrix row: Principal has V,E,X — no Create."""
        _user(roles["Principal"], "principal@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "principal@example.com")

        response = client.post("/api/v1/teachers/", _teacher_payload(), format="json")

        assert response.status_code == 403

    def test_staff_can_view_but_not_create_teacher(self, roles, wire_permissions):
        Teacher.objects.create(**_teacher_payload())
        _user(roles["Staff"], "staff@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "staff@example.com")

        list_response = client.get("/api/v1/teachers/")
        create_response = client.post("/api/v1/teachers/", _teacher_payload(email="other@example.com"), format="json")

        assert list_response.status_code == 200
        assert create_response.status_code == 403

    def test_teacher_role_sees_only_own_record(self, roles, wire_permissions):
        own_user = _user(roles["Teacher"], "teacher@example.com")
        Teacher.objects.create(user=own_user, **_teacher_payload())
        Teacher.objects.create(**_teacher_payload(first_name="Other", email="other@example.com"))
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.get("/api/v1/teachers/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["first_name"] == "Meera"

    def test_teacher_can_edit_own_record(self, roles, wire_permissions):
        own_user = _user(roles["Teacher"], "teacher@example.com")
        teacher = Teacher.objects.create(user=own_user, **_teacher_payload())
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.patch(f"/api/v1/teachers/{teacher.id}/", {"phone": "9999999999"}, format="json")

        assert response.status_code == 200
        assert response.data["phone"] == "9999999999"

    def test_student_gets_403_on_teachers_endpoint(self, roles, wire_permissions):
        """No RolePermission rows exist for Student on this module at all."""
        Teacher.objects.create(**_teacher_payload())
        _user(roles["Student"], "student@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get("/api/v1/teachers/")

        assert response.status_code == 403

    def test_soft_delete_preserves_teacher_row(self, roles, wire_permissions):
        teacher = Teacher.objects.create(**_teacher_payload())
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/teachers/{teacher.id}/")

        assert response.status_code == 204
        assert Teacher.objects.filter(pk=teacher.pk).count() == 0
        assert Teacher.all_with_deleted.filter(pk=teacher.pk, deleted_at__isnull=False).count() == 1

    def test_search_by_name(self, roles, wire_permissions):
        Teacher.objects.create(**_teacher_payload())
        Teacher.objects.create(**_teacher_payload(first_name="Ravi", last_name="Shah", email="ravi@example.com"))
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get("/api/v1/teachers/?search=Ravi")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["first_name"] == "Ravi"


@pytest.mark.django_db
class TestTeacherAssignment:
    def test_admin_can_assign_teacher_to_class_section_subject(self, roles, wire_permissions, class_section_subject):
        teacher = Teacher.objects.create(**_teacher_payload())
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/teacher-assignments/",
            {"teacher": teacher.id, "class_section_subject": class_section_subject.id},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["subject_code"] == "MATH"

    def test_duplicate_assignment_rejected(self, roles, wire_permissions, class_section_subject):
        teacher = Teacher.objects.create(**_teacher_payload())
        TeacherAssignment.objects.create(teacher=teacher, class_section_subject=class_section_subject)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/teacher-assignments/",
            {"teacher": teacher.id, "class_section_subject": class_section_subject.id},
            format="json",
        )

        assert response.status_code == 400

    def test_staff_cannot_create_assignment(self, roles, wire_permissions, class_section_subject):
        teacher = Teacher.objects.create(**_teacher_payload())
        _user(roles["Staff"], "staff@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "staff@example.com")

        response = client.post(
            "/api/v1/teacher-assignments/",
            {"teacher": teacher.id, "class_section_subject": class_section_subject.id},
            format="json",
        )

        assert response.status_code == 403

    def test_remove_assignment_is_hard_delete(self, roles, wire_permissions, class_section_subject):
        teacher = Teacher.objects.create(**_teacher_payload())
        assignment = TeacherAssignment.objects.create(teacher=teacher, class_section_subject=class_section_subject)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/teacher-assignments/{assignment.id}/")

        assert response.status_code == 204
        assert TeacherAssignment.objects.filter(pk=assignment.pk).count() == 0

    def test_teacher_sees_only_own_assignments(self, roles, wire_permissions, class_section_subject):
        own_user = _user(roles["Teacher"], "teacher@example.com")
        own_teacher = Teacher.objects.create(user=own_user, **_teacher_payload())
        other_teacher = Teacher.objects.create(**_teacher_payload(first_name="Other", email="other@example.com"))
        TeacherAssignment.objects.create(teacher=own_teacher, class_section_subject=class_section_subject)
        TeacherAssignment.objects.create(teacher=other_teacher, class_section_subject=class_section_subject)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.get("/api/v1/teacher-assignments/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["teacher"] == own_teacher.id
