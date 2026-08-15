import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User


@pytest.fixture
def student_role(db):
    return Role.objects.create(name="Student")


@pytest.fixture
def user(db, student_role):
    u = User.objects.create_user(email="jane@student.kathwadahighschool.edu.in", password="StrongPass123!")
    u.role = student_role
    u.save()
    return u


@pytest.mark.django_db
class TestAuthFlow:
    def test_me_requires_authentication(self):
        # DRF's SessionAuthentication returns 403 (not 401) for anonymous
        # requests, since it has no WWW-Authenticate challenge scheme — this
        # is documented DRF behavior, not a bug. Either way, access is denied.
        client = APIClient()
        response = client.get("/api/v1/auth/me/")
        assert response.status_code == 403

    def test_login_sets_httponly_session_cookie(self, user):
        client = APIClient(enforce_csrf_checks=False)
        response = client.post(
            "/api/v1/auth/login/",
            {"email": "jane@student.kathwadahighschool.edu.in", "password": "StrongPass123!"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["email"] == user.email
        assert response.data["role"] == "Student"
        # No password/hash ever leaves the server in the response body.
        assert "password" not in response.data

        session_cookie = client.cookies.get("sessionid")
        assert session_cookie is not None
        assert session_cookie["httponly"] is True

    def test_wrong_password_returns_401_generic_message(self, user):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/login/",
            {"email": "jane@student.kathwadahighschool.edu.in", "password": "wrong-password"},
            format="json",
        )
        assert response.status_code == 401
        assert response.data["detail"] == "Invalid email or password."

    def test_full_login_me_logout_cycle(self, user):
        client = APIClient(enforce_csrf_checks=False)

        login_response = client.post(
            "/api/v1/auth/login/",
            {"email": "jane@student.kathwadahighschool.edu.in", "password": "StrongPass123!"},
            format="json",
        )
        assert login_response.status_code == 200

        me_response = client.get("/api/v1/auth/me/")
        assert me_response.status_code == 200
        assert me_response.data["email"] == user.email

        logout_response = client.post("/api/v1/auth/logout/")
        assert logout_response.status_code == 204

        me_after_logout = client.get("/api/v1/auth/me/")
        assert me_after_logout.status_code == 403  # see note in test_me_requires_authentication
