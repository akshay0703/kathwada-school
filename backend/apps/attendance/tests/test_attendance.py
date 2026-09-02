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
from apps.attendance.models import AttendanceRecord
from apps.people.models import Enrollment, Student, Teacher, TeacherAssignment

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
def attendance_module(db):
    return Module.objects.create(key="attendance", label="Attendance")


@pytest.fixture
def wire_permissions(db, roles, attendance_module):
    """Mirrors the real seeded matrix (apps/accounts/management/commands/seed_permissions.py)."""
    matrix = {
        "Admin": [V, C, E, D, X],
        "Principal": [V, E],
        "Teacher": [V, C, E],
        "Staff": [V, C],
        "Student": [V],
        "Parent": [V],
    }
    for role_name, actions in matrix.items():
        for action in actions:
            RolePermission.objects.create(role=roles[role_name], module=attendance_module, action=action)


def _user(role, email):
    return User.objects.create_user(email=email, password="StrongPass123!", role=role)


def _login(client, email):
    return client.post("/api/v1/auth/login/", {"email": email, "password": "StrongPass123!"}, format="json")


@pytest.fixture
def class_section(db):
    academic_year = AcademicYear.objects.create(label="2026-27", start_date="2026-06-01", end_date="2027-04-30")
    school_class = SchoolClass.objects.create(name="Std 10", order=10)
    section = Section.objects.create(name="A")
    return ClassSection.objects.create(school_class=school_class, section=section, academic_year=academic_year)


@pytest.fixture
def enrolled_student(db, class_section):
    student = Student.objects.create(
        admission_no="KHS-2026-0001", first_name="Aarav", last_name="Patel", dob="2012-05-14"
    )
    Enrollment.objects.create(student=student, class_section=class_section, roll_no=1)
    return student


@pytest.fixture
def other_enrolled_student(db, class_section):
    student = Student.objects.create(
        admission_no="KHS-2026-0002", first_name="Diya", last_name="Shah", dob="2012-01-01"
    )
    Enrollment.objects.create(student=student, class_section=class_section, roll_no=2)
    return student


@pytest.mark.django_db
class TestAttendancePermissions:
    def test_admin_can_mark_attendance(self, roles, wire_permissions, class_section, enrolled_student):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/attendance/",
            {"student": enrolled_student.id, "class_section": class_section.id, "date": "2026-07-01", "status": "present"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["status"] == "present"
        assert response.data["marked_by_email"] == "admin@example.com"

    def test_staff_can_create_but_not_edit(self, roles, wire_permissions, class_section, enrolled_student):
        _user(roles["Staff"], "staff@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "staff@example.com")

        create_response = client.post(
            "/api/v1/attendance/",
            {"student": enrolled_student.id, "class_section": class_section.id, "date": "2026-07-01", "status": "present"},
            format="json",
        )
        edit_response = client.patch(
            f"/api/v1/attendance/{create_response.data['id']}/", {"status": "absent"}, format="json"
        )

        assert create_response.status_code == 201
        assert edit_response.status_code == 403

    def test_principal_cannot_create(self, roles, wire_permissions, class_section, enrolled_student):
        """Attendance matrix row: Principal has V,E — no Create."""
        _user(roles["Principal"], "principal@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "principal@example.com")

        response = client.post(
            "/api/v1/attendance/",
            {"student": enrolled_student.id, "class_section": class_section.id, "date": "2026-07-01", "status": "present"},
            format="json",
        )

        assert response.status_code == 403

    def test_student_sees_only_own_records(self, roles, wire_permissions, class_section, enrolled_student, other_enrolled_student):
        own_user = _user(roles["Student"], "student@example.com")
        enrolled_student.user = own_user
        enrolled_student.save()
        AttendanceRecord.objects.create(student=enrolled_student, class_section=class_section, date="2026-07-01", status="present")
        AttendanceRecord.objects.create(student=other_enrolled_student, class_section=class_section, date="2026-07-01", status="absent")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get("/api/v1/attendance/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["student"] == enrolled_student.id

    def test_student_cannot_create(self, roles, wire_permissions, class_section, enrolled_student):
        _user(roles["Student"], "student@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.post(
            "/api/v1/attendance/",
            {"student": enrolled_student.id, "class_section": class_section.id, "date": "2026-07-01", "status": "present"},
            format="json",
        )

        assert response.status_code == 403

    def test_parent_gets_empty_queryset(self, roles, wire_permissions, class_section, enrolled_student):
        """Guardian/StudentGuardian doesn't exist yet — deny by default, not full access."""
        AttendanceRecord.objects.create(student=enrolled_student, class_section=class_section, date="2026-07-01", status="present")
        _user(roles["Parent"], "parent@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/attendance/")

        assert response.status_code == 200
        assert response.data["count"] == 0


@pytest.mark.django_db
class TestAttendanceValidation:
    def test_duplicate_record_same_student_date_rejected(self, roles, wire_permissions, class_section, enrolled_student):
        AttendanceRecord.objects.create(student=enrolled_student, class_section=class_section, date="2026-07-01", status="present")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/attendance/",
            {"student": enrolled_student.id, "class_section": class_section.id, "date": "2026-07-01", "status": "absent"},
            format="json",
        )

        assert response.status_code == 400

    def test_non_enrolled_student_rejected(self, roles, wire_permissions, class_section):
        outsider = Student.objects.create(admission_no="KHS-2026-9999", first_name="X", last_name="Y", dob="2012-01-01")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/attendance/",
            {"student": outsider.id, "class_section": class_section.id, "date": "2026-07-01", "status": "present"},
            format="json",
        )

        assert response.status_code == 400

    def test_edit_status_updates_existing_record(self, roles, wire_permissions, class_section, enrolled_student):
        record = AttendanceRecord.objects.create(student=enrolled_student, class_section=class_section, date="2026-07-01", status="present")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.patch(f"/api/v1/attendance/{record.id}/", {"status": "late"}, format="json")

        assert response.status_code == 200
        assert response.data["status"] == "late"

    def test_soft_delete_preserves_row(self, roles, wire_permissions, class_section, enrolled_student):
        record = AttendanceRecord.objects.create(student=enrolled_student, class_section=class_section, date="2026-07-01", status="present")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/attendance/{record.id}/")

        assert response.status_code == 204
        assert AttendanceRecord.objects.filter(pk=record.pk).count() == 0
        assert AttendanceRecord.all_with_deleted.filter(pk=record.pk, deleted_at__isnull=False).count() == 1

    def test_filter_by_class_section_and_date(self, roles, wire_permissions, class_section, enrolled_student, other_enrolled_student):
        AttendanceRecord.objects.create(student=enrolled_student, class_section=class_section, date="2026-07-01", status="present")
        AttendanceRecord.objects.create(student=other_enrolled_student, class_section=class_section, date="2026-07-02", status="absent")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get(f"/api/v1/attendance/?class_section={class_section.id}&date=2026-07-01")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["date"] == "2026-07-01"


@pytest.mark.django_db
class TestBulkMark:
    def test_bulk_mark_creates_records_for_all_students(
        self, roles, wire_permissions, class_section, enrolled_student, other_enrolled_student
    ):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/attendance/bulk-mark/",
            {
                "class_section": class_section.id,
                "date": "2026-07-01",
                "records": [
                    {"student": enrolled_student.id, "status": "present"},
                    {"student": other_enrolled_student.id, "status": "absent"},
                ],
            },
            format="json",
        )

        assert response.status_code == 201
        assert len(response.data) == 2
        assert AttendanceRecord.objects.filter(class_section=class_section, date="2026-07-01").count() == 2

    def test_bulk_mark_rejects_non_enrolled_student(self, roles, wire_permissions, class_section, enrolled_student):
        outsider = Student.objects.create(admission_no="KHS-2026-8888", first_name="Not", last_name="Enrolled", dob="2012-01-01")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/attendance/bulk-mark/",
            {
                "class_section": class_section.id,
                "date": "2026-07-01",
                "records": [{"student": outsider.id, "status": "present"}],
            },
            format="json",
        )

        assert response.status_code == 400

    def test_bulk_mark_is_idempotent_correction(self, roles, wire_permissions, class_section, enrolled_student):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")
        client.post(
            "/api/v1/attendance/bulk-mark/",
            {"class_section": class_section.id, "date": "2026-07-01", "records": [{"student": enrolled_student.id, "status": "present"}]},
            format="json",
        )

        response = client.post(
            "/api/v1/attendance/bulk-mark/",
            {"class_section": class_section.id, "date": "2026-07-01", "records": [{"student": enrolled_student.id, "status": "absent"}]},
            format="json",
        )

        assert response.status_code == 201
        assert AttendanceRecord.objects.filter(student=enrolled_student, date="2026-07-01").count() == 1
        assert AttendanceRecord.objects.get(student=enrolled_student, date="2026-07-01").status == "absent"

    def test_teacher_can_only_bulk_mark_assigned_class_section(self, roles, wire_permissions, class_section, enrolled_student):
        academic_year2 = AcademicYear.objects.create(label="2027-28", start_date="2027-06-01", end_date="2028-04-30")
        other_section = Section.objects.create(name="B")
        other_class_section = ClassSection.objects.create(
            school_class=class_section.school_class, section=other_section, academic_year=academic_year2
        )
        subject = Subject.objects.create(name="Mathematics", code="MATH")
        css = ClassSectionSubject.objects.create(class_section=class_section, subject=subject)

        teacher_user = _user(roles["Teacher"], "teacher@example.com")
        teacher = Teacher.objects.create(user=teacher_user, first_name="Meera", last_name="Joshi")
        TeacherAssignment.objects.create(teacher=teacher, class_section_subject=css)

        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        allowed_response = client.post(
            "/api/v1/attendance/bulk-mark/",
            {"class_section": class_section.id, "date": "2026-07-01", "records": [{"student": enrolled_student.id, "status": "present"}]},
            format="json",
        )
        denied_response = client.post(
            "/api/v1/attendance/bulk-mark/",
            {"class_section": other_class_section.id, "date": "2027-07-01", "records": []},
            format="json",
        )

        assert allowed_response.status_code == 201
        assert denied_response.status_code == 403
