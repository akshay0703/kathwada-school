import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Module, PermissionAction, Role, RolePermission, User


@pytest.fixture
def roles(db):
    return {
        "Admin": Role.objects.create(name="Admin"),
        "Student": Role.objects.create(name="Student"),
    }


@pytest.fixture
def users_module(db):
    return Module.objects.create(key="users", label="Users & Role Management")


@pytest.fixture
def wire_admin_permission(db, roles, users_module):
    RolePermission.objects.create(role=roles["Admin"], module=users_module, action=PermissionAction.VIEW)


def _login(client, email, password):
    return client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")


@pytest.mark.django_db
class TestRolePermissionScaffold:
    def test_student_gets_403_on_admin_only_stub_endpoint(self, roles, wire_admin_permission):
        User.objects.create_user(email="student@example.com", password="StrongPass123!", role=roles["Student"])
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com", "StrongPass123!")

        response = client.get("/api/v1/auth/admin-stub/")

        assert response.status_code == 403

    def test_admin_gets_200_on_same_stub_endpoint(self, roles, wire_admin_permission):
        User.objects.create_user(email="admin@example.com", password="StrongPass123!", role=roles["Admin"])
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com", "StrongPass123!")

        response = client.get("/api/v1/auth/admin-stub/")

        assert response.status_code == 200
        assert response.data["detail"] == "You have Admin-level access."

    def test_unauthenticated_request_is_denied(self, wire_admin_permission):
        # DRF's SessionAuthentication returns 403 (not 401) for anonymous
        # requests — see note in test_auth_flow.py. Either way, denied.
        client = APIClient()
        response = client.get("/api/v1/auth/admin-stub/")
        assert response.status_code == 403
