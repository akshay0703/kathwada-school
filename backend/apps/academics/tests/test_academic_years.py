from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear
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
def academic_years_module(db):
    return Module.objects.create(key="academic_years", label="Academic Years")


@pytest.fixture
def wire_permissions(db, roles, academic_years_module):
    """Mirrors the real seeded matrix (apps/accounts/management/commands/seed_permissions.py)."""
    matrix = {
        "Admin": [V, C, E, D, X],
        "Principal": [V, C, E, X],
        "Teacher": [V],
        "Student": [V],
        "Parent": [V],
    }
    for role_name, actions in matrix.items():
        for action in actions:
            RolePermission.objects.create(role=roles[role_name], module=academic_years_module, action=action)


def _user(role, email):
    return User.objects.create_user(email=email, password="StrongPass123!", role=role)


def _login(client, email):
    return client.post("/api/v1/auth/login/", {"email": email, "password": "StrongPass123!"}, format="json")


def _year_payload(**overrides):
    payload = {
        "label": "2026-27",
        "start_date": "2026-06-01",
        "end_date": "2027-04-30",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestAcademicYearPermissions:
    """Scenarios 1-6 from the Phase 1.1 spec: role-based write access."""

    def test_admin_can_create_academic_year(self, roles, wire_permissions):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/academic-years/", _year_payload(), format="json")

        assert response.status_code == 201
        assert response.data["label"] == "2026-27"

    def test_principal_can_create_academic_year(self, roles, wire_permissions):
        _user(roles["Principal"], "principal@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "principal@example.com")

        response = client.post("/api/v1/academic-years/", _year_payload(), format="json")

        assert response.status_code == 201

    def test_teacher_cannot_create_academic_year(self, roles, wire_permissions):
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.post("/api/v1/academic-years/", _year_payload(), format="json")

        assert response.status_code == 403

    def test_student_cannot_create_academic_year(self, roles, wire_permissions):
        _user(roles["Student"], "student@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.post("/api/v1/academic-years/", _year_payload(), format="json")

        assert response.status_code == 403

    def test_parent_cannot_create_academic_year(self, roles, wire_permissions):
        _user(roles["Parent"], "parent@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.post("/api/v1/academic-years/", _year_payload(), format="json")

        assert response.status_code == 403

    def test_anonymous_user_cannot_access_protected_endpoints(self, wire_permissions):
        client = APIClient()

        list_response = client.get("/api/v1/academic-years/")
        create_response = client.post("/api/v1/academic-years/", _year_payload(), format="json")

        # DRF's SessionAuthentication returns 403 (not 401) for anonymous
        # requests — documented DRF behavior, see apps/accounts/tests/
        # test_auth_flow.py's note. Either way, access is denied.
        assert list_response.status_code == 403
        assert create_response.status_code == 403

    def test_principal_cannot_delete_academic_year(self, roles, wire_permissions):
        """Explicit Phase 1.1 deviation: Principal has C+E but not D — see
        apps/accounts/management/commands/seed_permissions.py's comment."""
        year = AcademicYear.objects.create(label="2025-26", start_date=date(2025, 6, 1), end_date=date(2026, 4, 30))
        _user(roles["Principal"], "principal@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "principal@example.com")

        response = client.delete(f"/api/v1/academic-years/{year.pk}/")

        assert response.status_code == 403

    def test_teacher_can_view_academic_years(self, roles, wire_permissions):
        AcademicYear.objects.create(label="2025-26", start_date=date(2025, 6, 1), end_date=date(2026, 4, 30))
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.get("/api/v1/academic-years/")

        assert response.status_code == 200
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestAcademicYearBusinessRules:
    """Scenarios 7-10: only-one-current, historical data intact, validation."""

    def test_only_one_academic_year_can_be_current(self, roles, wire_permissions):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        first = client.post("/api/v1/academic-years/", _year_payload(label="2025-26", start_date="2025-06-01", end_date="2026-04-30"), format="json")
        second = client.post("/api/v1/academic-years/", _year_payload(label="2026-27"), format="json")
        assert first.status_code == 201 and second.status_code == 201

        mark_first = client.post(f"/api/v1/academic-years/{first.data['id']}/mark-current/")
        assert mark_first.status_code == 200
        assert mark_first.data["is_current"] is True

        mark_second = client.post(f"/api/v1/academic-years/{second.data['id']}/mark-current/")
        assert mark_second.status_code == 200

        first_reloaded = AcademicYear.objects.get(pk=first.data["id"])
        second_reloaded = AcademicYear.objects.get(pk=second.data["id"])
        assert first_reloaded.is_current is False, "marking a new year current must unset the previous one"
        assert second_reloaded.is_current is True
        assert AcademicYear.objects.filter(is_current=True).count() == 1

    def test_historical_academic_year_remains_unchanged_on_delete(self, roles, wire_permissions):
        year = AcademicYear.objects.create(
            label="2024-25", start_date=date(2024, 6, 1), end_date=date(2025, 4, 30)
        )
        year_id = year.pk
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/academic-years/{year_id}/")

        assert response.status_code == 204
        # The row itself must still exist — "historical data must remain
        # intact" is a hard DB-level guarantee (soft delete), not a promise.
        still_exists = AcademicYear.all_with_deleted.filter(pk=year_id).first()
        assert still_exists is not None
        assert still_exists.label == "2024-25"
        assert still_exists.deleted_at is not None
        # But it no longer appears in normal (non-deleted) queries/listings.
        assert not AcademicYear.objects.filter(pk=year_id).exists()

    def test_invalid_date_range_is_rejected(self, roles, wire_permissions):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/academic-years/",
            _year_payload(start_date="2027-01-01", end_date="2026-01-01"),
            format="json",
        )

        assert response.status_code == 400

    def test_overlapping_date_range_is_rejected(self, roles, wire_permissions):
        AcademicYear.objects.create(label="2025-26", start_date=date(2025, 6, 1), end_date=date(2026, 4, 30))
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/academic-years/",
            _year_payload(label="overlapping", start_date="2026-01-01", end_date="2026-12-31"),
            format="json",
        )

        assert response.status_code == 400

    def test_api_validation_rejects_missing_required_fields(self, roles, wire_permissions):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post("/api/v1/academic-years/", {"label": "incomplete"}, format="json")

        assert response.status_code == 400
        assert "start_date" in response.data
        assert "end_date" in response.data

    def test_duplicate_label_for_same_school_is_rejected(self, roles, wire_permissions):
        AcademicYear.objects.create(label="2025-26", start_date=date(2025, 6, 1), end_date=date(2026, 4, 30))
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/academic-years/",
            _year_payload(label="2025-26", start_date="2030-01-01", end_date="2031-01-01"),
            format="json",
        )

        assert response.status_code == 400
