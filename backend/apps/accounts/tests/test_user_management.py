import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Module, PermissionAction, Role, RolePermission, User
from apps.people.models import Student

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
def users_module(db):
    return Module.objects.create(key="users", label="Users & Role Management")


@pytest.fixture
def wire_permissions(db, roles, users_module):
    """Mirrors the real seeded matrix: "users" is Admin-only, nothing for anyone else."""
    for action in [V, C, E, D, X]:
        RolePermission.objects.create(role=roles["Admin"], module=users_module, action=action)


def _admin(roles, email="admin@example.com"):
    return User.objects.create_user(email=email, password="StrongPass123!", role=roles["Admin"])


def _login(client, email):
    return client.post("/api/v1/auth/login/", {"email": email, "password": "StrongPass123!"}, format="json")


@pytest.mark.django_db
class TestUserManagementPermissions:
    def test_admin_can_create_user(self, roles, wire_permissions):
        _admin(roles)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/auth/users/",
            {"email": "newteacher@example.com", "password": "AValidPass123!", "role_id": roles["Teacher"].id},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["email"] == "newteacher@example.com"
        assert response.data["role"] == "Teacher"
        assert "password" not in response.data

    def test_password_never_appears_in_response(self, roles, wire_permissions):
        _admin(roles)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        create_response = client.post(
            "/api/v1/auth/users/", {"email": "x@example.com", "password": "AValidPass123!"}, format="json"
        )
        list_response = client.get("/api/v1/auth/users/")
        retrieve_response = client.get(f"/api/v1/auth/users/{create_response.data['id']}/")

        assert "password" not in create_response.data
        assert all("password" not in u for u in list_response.data["results"])
        assert "password" not in retrieve_response.data

    def test_create_rejects_weak_password(self, roles, wire_permissions):
        _admin(roles)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/auth/users/", {"email": "weak@example.com", "password": "123"}, format="json")

        assert response.status_code == 400
        assert "password" in response.data

    def test_create_requires_password(self, roles, wire_permissions):
        _admin(roles)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/auth/users/", {"email": "nopassword@example.com"}, format="json")

        assert response.status_code == 400
        assert "password" in response.data

    def test_non_admin_role_has_no_access(self, roles, wire_permissions):
        """The "users" module has zero RolePermission rows for any role but Admin."""
        User.objects.create_user(email="teacher@example.com", password="StrongPass123!", role=roles["Teacher"])
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.get("/api/v1/auth/users/")

        assert response.status_code == 403

    def test_admin_can_change_role(self, roles, wire_permissions):
        _admin(roles)
        target = User.objects.create_user(email="target@example.com", password="StrongPass123!", role=roles["Staff"])
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.patch(f"/api/v1/auth/users/{target.id}/", {"role_id": roles["Teacher"].id}, format="json")

        assert response.status_code == 200
        assert response.data["role"] == "Teacher"

    def test_admin_can_deactivate_and_reactivate_user(self, roles, wire_permissions):
        _admin(roles)
        target = User.objects.create_user(email="target@example.com", password="StrongPass123!", role=roles["Teacher"])
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        deactivate_response = client.patch(f"/api/v1/auth/users/{target.id}/", {"is_active": False}, format="json")
        target.refresh_from_db()
        login_while_inactive = client.post(
            "/api/v1/auth/login/", {"email": "target@example.com", "password": "StrongPass123!"}, format="json"
        )
        reactivate_response = client.patch(f"/api/v1/auth/users/{target.id}/", {"is_active": True}, format="json")

        assert deactivate_response.status_code == 200
        assert target.is_active is False
        assert login_while_inactive.status_code == 401
        assert reactivate_response.status_code == 200
        assert reactivate_response.data["is_active"] is True

    def test_patch_cannot_change_password_directly(self, roles, wire_permissions):
        _admin(roles)
        target = User.objects.create_user(email="target@example.com", password="OriginalPass123!", role=roles["Teacher"])
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        client.patch(f"/api/v1/auth/users/{target.id}/", {"password": "ShouldNotApply123!"}, format="json")
        target.refresh_from_db()

        assert target.check_password("OriginalPass123!")
        assert not target.check_password("ShouldNotApply123!")

    def test_set_password_action_changes_password(self, roles, wire_permissions):
        _admin(roles)
        target = User.objects.create_user(email="target@example.com", password="OriginalPass123!", role=roles["Teacher"])
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(f"/api/v1/auth/users/{target.id}/set-password/", {"password": "BrandNewPass123!"}, format="json")
        target.refresh_from_db()

        assert response.status_code == 200
        assert "password" not in response.data
        assert target.check_password("BrandNewPass123!")

    def test_set_password_rejects_weak_password(self, roles, wire_permissions):
        _admin(roles)
        target = User.objects.create_user(email="target@example.com", password="OriginalPass123!", role=roles["Teacher"])
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(f"/api/v1/auth/users/{target.id}/set-password/", {"password": "123"}, format="json")
        target.refresh_from_db()

        assert response.status_code == 400
        assert target.check_password("OriginalPass123!")

    def test_delete_is_not_allowed(self, roles, wire_permissions):
        """
        DELETE is blocked two ways: `destroy` isn't in permission_action_map
        at all (so HasModulePermission denies it with 403 before DRF even
        looks up a handler), and http_method_names excludes DELETE outright
        as a second layer. Either way the row must survive.
        """
        _admin(roles)
        target = User.objects.create_user(email="target@example.com", password="StrongPass123!", role=roles["Teacher"])
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/auth/users/{target.id}/")

        assert response.status_code in (403, 405)
        assert User.objects.filter(pk=target.pk).exists()

    def test_search_by_email(self, roles, wire_permissions):
        _admin(roles)
        User.objects.create_user(email="meera.joshi@example.com", password="StrongPass123!", role=roles["Teacher"])
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get("/api/v1/auth/users/?search=meera")

        assert response.status_code == 200
        assert response.data["count"] == 1


@pytest.mark.django_db
class TestRoleListEndpoint:
    def test_admin_can_list_roles(self, roles, wire_permissions):
        _admin(roles)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get("/api/v1/auth/roles/")

        assert response.status_code == 200
        assert response.data["count"] == 6


@pytest.mark.django_db
class TestLinkUserToProfile:
    """
    Linking a User to a Student/Teacher/Guardian profile reuses the
    existing, already-writable `user` field on those serializers (no new
    endpoint needed) — these tests confirm that flow end-to-end from the
    User Management side, plus the `unlinked=true` filter added to help
    the linking UI find candidates.
    """

    def test_unlinked_filter_excludes_already_linked_students(self, roles, wire_permissions):
        students_module = Module.objects.create(key="students", label="Students")
        for action in [V, C, E, D, X]:
            RolePermission.objects.create(role=roles["Admin"], module=students_module, action=action)
        _admin(roles)
        linked_user = User.objects.create_user(email="linked@example.com", password="StrongPass123!", role=roles["Student"])
        Student.objects.create(user=linked_user, admission_no="KHS-2026-0001", first_name="Aarav", last_name="Patel", dob="2012-05-14")
        Student.objects.create(admission_no="KHS-2026-0002", first_name="Diya", last_name="Shah", dob="2012-01-01")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get("/api/v1/students/?unlinked=true")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["admission_no"] == "KHS-2026-0002"

    def test_linking_via_existing_student_endpoint(self, roles, wire_permissions):
        students_module = Module.objects.create(key="students", label="Students")
        for action in [V, C, E, D, X]:
            RolePermission.objects.create(role=roles["Admin"], module=students_module, action=action)
        _admin(roles)
        new_user = User.objects.create_user(email="newlogin@example.com", password="StrongPass123!", role=roles["Student"])
        student = Student.objects.create(admission_no="KHS-2026-0003", first_name="Ishaan", last_name="Mehta", dob="2012-03-03")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.patch(f"/api/v1/students/{student.id}/", {"user": new_user.id}, format="json")
        student.refresh_from_db()

        assert response.status_code == 200
        assert student.user_id == new_user.id
