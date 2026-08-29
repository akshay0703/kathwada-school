import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, ClassSection, SchoolClass, Section, Subject
from apps.accounts.models import Module, PermissionAction, Role, RolePermission, User

V, C, E, D, X = (
    PermissionAction.VIEW,
    PermissionAction.CREATE,
    PermissionAction.EDIT,
    PermissionAction.DELETE,
    PermissionAction.EXPORT,
)


@pytest.fixture
def roles(db):
    return {name: Role.objects.create(name=name) for name in ["Admin", "Principal", "Teacher", "Student", "Parent"]}


@pytest.fixture
def modules(db):
    return {
        "classes_sections": Module.objects.create(key="classes_sections", label="Classes / Sections"),
        "subjects": Module.objects.create(key="subjects", label="Subjects"),
    }


@pytest.fixture
def wire_permissions(db, roles, modules):
    """Mirrors the real seeded matrix (apps/accounts/management/commands/seed_permissions.py)."""
    matrix = {
        "classes_sections": {
            "Admin": [V, C, E, D, X],
            "Principal": [V, C, E, X],
            "Teacher": [V],
            "Student": [V],
            "Parent": [V],
        },
        "subjects": {
            "Admin": [V, C, E, D, X],
            "Principal": [V, E, X],
            "Teacher": [V],
            "Student": [V],
            "Parent": [V],
        },
    }
    for module_key, role_actions in matrix.items():
        for role_name, actions in role_actions.items():
            for action in actions:
                RolePermission.objects.create(role=roles[role_name], module=modules[module_key], action=action)


def _user(role, email):
    return User.objects.create_user(email=email, password="StrongPass123!", role=role)


def _login(client, email):
    return client.post("/api/v1/auth/login/", {"email": email, "password": "StrongPass123!"}, format="json")


@pytest.fixture
def academic_year(db):
    return AcademicYear.objects.create(label="2026-27", start_date="2026-06-01", end_date="2027-04-30")


@pytest.mark.django_db
class TestSchoolClassPermissions:
    def test_admin_can_create_class(self, roles, wire_permissions):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/classes/", {"name": "Std 10", "order": 10}, format="json")

        assert response.status_code == 201
        assert response.data["name"] == "Std 10"

    def test_teacher_cannot_create_class(self, roles, wire_permissions):
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.post("/api/v1/classes/", {"name": "Std 10", "order": 10}, format="json")

        assert response.status_code == 403

    def test_student_can_view_but_not_create_class(self, roles, wire_permissions):
        SchoolClass.objects.create(name="Std 9", order=9)
        _user(roles["Student"], "student@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        list_response = client.get("/api/v1/classes/")
        create_response = client.post("/api/v1/classes/", {"name": "Std 11", "order": 11}, format="json")

        assert list_response.status_code == 200
        assert create_response.status_code == 403

    def test_class_name_unique(self, roles, wire_permissions):
        SchoolClass.objects.create(name="Std 10", order=10)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/classes/", {"name": "Std 10", "order": 10}, format="json")

        assert response.status_code == 400

    def test_soft_delete_preserves_class_row(self, roles, wire_permissions):
        school_class = SchoolClass.objects.create(name="Std 8", order=8)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/classes/{school_class.id}/")

        assert response.status_code == 204
        assert SchoolClass.objects.filter(pk=school_class.pk).count() == 0  # excluded from default manager
        assert SchoolClass.all_with_deleted.filter(pk=school_class.pk, deleted_at__isnull=False).count() == 1


@pytest.mark.django_db
class TestSubjectPermissions:
    def test_admin_can_create_subject(self, roles, wire_permissions):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/subjects/", {"name": "Mathematics", "code": "MATH"}, format="json")

        assert response.status_code == 201

    def test_principal_cannot_create_subject(self, roles, wire_permissions):
        """Subjects matrix row: Principal has V,E,X — no Create."""
        _user(roles["Principal"], "principal@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "principal@example.com")

        response = client.post("/api/v1/subjects/", {"name": "Science", "code": "SCI"}, format="json")

        assert response.status_code == 403

    def test_subject_code_unique(self, roles, wire_permissions):
        Subject.objects.create(name="Mathematics", code="MATH")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/subjects/", {"name": "Maths II", "code": "MATH"}, format="json")

        assert response.status_code == 400


@pytest.mark.django_db
class TestClassSectionAndOfferings:
    def test_admin_can_create_class_section(self, roles, wire_permissions, academic_year):
        school_class = SchoolClass.objects.create(name="Std 10", order=10)
        section = Section.objects.create(name="A")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/class-sections/",
            {"school_class": school_class.id, "section": section.id, "academic_year": academic_year.id},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["school_class_name"] == "Std 10"
        assert response.data["section_name"] == "A"

    def test_duplicate_class_section_per_year_rejected(self, roles, wire_permissions, academic_year):
        school_class = SchoolClass.objects.create(name="Std 10", order=10)
        section = Section.objects.create(name="A")
        ClassSection.objects.create(school_class=school_class, section=section, academic_year=academic_year)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/class-sections/",
            {"school_class": school_class.id, "section": section.id, "academic_year": academic_year.id},
            format="json",
        )

        assert response.status_code == 400

    def test_teacher_cannot_create_class_section(self, roles, wire_permissions, academic_year):
        school_class = SchoolClass.objects.create(name="Std 10", order=10)
        section = Section.objects.create(name="B")
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.post(
            "/api/v1/class-sections/",
            {"school_class": school_class.id, "section": section.id, "academic_year": academic_year.id},
            format="json",
        )

        assert response.status_code == 403

    def test_assign_subject_to_class_section(self, roles, wire_permissions, academic_year):
        school_class = SchoolClass.objects.create(name="Std 10", order=10)
        section = Section.objects.create(name="A")
        class_section = ClassSection.objects.create(school_class=school_class, section=section, academic_year=academic_year)
        subject = Subject.objects.create(name="Mathematics", code="MATH")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(f"/api/v1/class-sections/{class_section.id}/subjects/", {"subject": subject.id}, format="json")

        assert response.status_code == 201
        assert response.data["subject_code"] == "MATH"

    def test_duplicate_subject_assignment_rejected(self, roles, wire_permissions, academic_year):
        school_class = SchoolClass.objects.create(name="Std 10", order=10)
        section = Section.objects.create(name="A")
        class_section = ClassSection.objects.create(school_class=school_class, section=section, academic_year=academic_year)
        subject = Subject.objects.create(name="Mathematics", code="MATH")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")
        client.post(f"/api/v1/class-sections/{class_section.id}/subjects/", {"subject": subject.id}, format="json")

        response = client.post(f"/api/v1/class-sections/{class_section.id}/subjects/", {"subject": subject.id}, format="json")

        assert response.status_code == 400

    def test_remove_subject_from_class_section(self, roles, wire_permissions, academic_year):
        school_class = SchoolClass.objects.create(name="Std 10", order=10)
        section = Section.objects.create(name="A")
        class_section = ClassSection.objects.create(school_class=school_class, section=section, academic_year=academic_year)
        subject = Subject.objects.create(name="Mathematics", code="MATH")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")
        client.post(f"/api/v1/class-sections/{class_section.id}/subjects/", {"subject": subject.id}, format="json")

        response = client.post(f"/api/v1/class-sections/{class_section.id}/subjects/remove/", {"subject": subject.id}, format="json")
        get_response = client.get(f"/api/v1/class-sections/{class_section.id}/")

        assert response.status_code == 204
        assert get_response.data["subjects"] == []

    def test_soft_delete_class_section_preserves_row(self, roles, wire_permissions, academic_year):
        school_class = SchoolClass.objects.create(name="Std 10", order=10)
        section = Section.objects.create(name="A")
        class_section = ClassSection.objects.create(school_class=school_class, section=section, academic_year=academic_year)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/class-sections/{class_section.id}/")

        assert response.status_code == 204
        assert ClassSection.objects.filter(pk=class_section.pk).count() == 0
        assert ClassSection.all_with_deleted.filter(pk=class_section.pk, deleted_at__isnull=False).count() == 1
