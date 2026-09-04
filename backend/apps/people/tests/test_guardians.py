import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, ClassSection, SchoolClass, Section
from apps.accounts.models import Module, PermissionAction, Role, RolePermission, User
from apps.attendance.models import AttendanceRecord
from apps.exams.models import Exam, ExamSubject
from apps.fees.models import FeeInvoice, FeeStructure
from apps.marks.models import Mark
from apps.people.models import Enrollment, Guardian, Student, StudentGuardian

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
def all_modules(db):
    keys = ["guardians", "students", "attendance", "marks", "fees"]
    return {key: Module.objects.create(key=key, label=key) for key in keys}


@pytest.fixture
def wire_permissions(db, roles, all_modules):
    """Mirrors the real seeded matrix (apps/accounts/management/commands/seed_permissions.py)."""
    matrix = {
        "guardians": {
            "Admin": [V, C, E, D, X], "Principal": [V, E, X], "Teacher": [V],
            "Staff": [V, C, E, X], "Parent": [V, E],
        },
        "students": {
            "Admin": [V, C, E, D, X], "Principal": [V, C, E, X], "Teacher": [V],
            "Staff": [V, C, E, X], "Student": [V], "Parent": [V],
        },
        "attendance": {
            "Admin": [V, C, E, D, X], "Principal": [V, E], "Teacher": [V, C, E],
            "Staff": [V, C], "Student": [V], "Parent": [V],
        },
        "marks": {
            "Admin": [V, C, E, D, X], "Principal": [V, E], "Teacher": [V, C, E],
            "Student": [V], "Parent": [V],
        },
        "fees": {
            "Admin": [V, C, E, D, X], "Principal": [V, X], "Staff": [V, C, E, X],
            "Student": [V], "Parent": [V, X],
        },
    }
    for module_key, role_actions in matrix.items():
        module = all_modules[module_key]
        for role_name, actions in role_actions.items():
            for action in actions:
                RolePermission.objects.create(role=roles[role_name], module=module, action=action)


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
def student(db, class_section):
    student = Student.objects.create(admission_no="KHS-2026-0001", first_name="Aarav", last_name="Patel", dob="2012-05-14")
    Enrollment.objects.create(student=student, class_section=class_section, roll_no=1)
    return student


@pytest.fixture
def other_student(db, class_section):
    student = Student.objects.create(admission_no="KHS-2026-0002", first_name="Diya", last_name="Shah", dob="2012-01-01")
    Enrollment.objects.create(student=student, class_section=class_section, roll_no=2)
    return student


@pytest.mark.django_db
class TestGuardianPermissions:
    def test_admin_can_create_guardian(self, roles, wire_permissions):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/guardians/",
            {"name": "Rakesh Patel", "phone": "9876543210", "email": "rakesh@example.com", "relationship": "father"},
            format="json",
        )

        assert response.status_code == 201

    def test_student_role_has_no_access(self, roles, wire_permissions):
        """Guardians matrix row: Student gets no rows at all."""
        _user(roles["Student"], "student@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get("/api/v1/guardians/")

        assert response.status_code == 403

    def test_parent_sees_only_own_record(self, roles, wire_permissions):
        own_user = _user(roles["Parent"], "parent@example.com")
        Guardian.objects.create(user=own_user, name="Rakesh Patel", relationship="father")
        Guardian.objects.create(name="Other Guardian", relationship="mother")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/guardians/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["name"] == "Rakesh Patel"

    def test_parent_can_edit_own_record(self, roles, wire_permissions):
        own_user = _user(roles["Parent"], "parent@example.com")
        guardian = Guardian.objects.create(user=own_user, name="Rakesh Patel", relationship="father")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.patch(f"/api/v1/guardians/{guardian.id}/", {"phone": "9999999999"}, format="json")

        assert response.status_code == 200
        assert response.data["phone"] == "9999999999"

    def test_soft_delete_preserves_guardian_row(self, roles, wire_permissions):
        guardian = Guardian.objects.create(name="Rakesh Patel", relationship="father")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/guardians/{guardian.id}/")

        assert response.status_code == 204
        assert Guardian.objects.filter(pk=guardian.pk).count() == 0
        assert Guardian.all_with_deleted.filter(pk=guardian.pk, deleted_at__isnull=False).count() == 1


@pytest.mark.django_db
class TestStudentGuardianLink:
    def test_admin_can_link_guardian_to_student(self, roles, wire_permissions, student):
        guardian = Guardian.objects.create(name="Rakesh Patel", relationship="father")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/student-guardians/",
            {"student": student.id, "guardian": guardian.id, "is_primary_contact": True},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["is_primary_contact"] is True

    def test_duplicate_link_rejected(self, roles, wire_permissions, student):
        guardian = Guardian.objects.create(name="Rakesh Patel", relationship="father")
        StudentGuardian.objects.create(student=student, guardian=guardian)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/student-guardians/",
            {"student": student.id, "guardian": guardian.id},
            format="json",
        )

        assert response.status_code == 400


@pytest.mark.django_db
class TestParentScopingIntegration:
    """
    Verifies the actual "integration" ask: Parent role now resolves real
    scoping (via StudentGuardian) across every module that previously
    documented this as a gap — Student, Enrollment, Attendance, Marks, Fees
    — instead of returning an empty queryset unconditionally.
    """

    def test_parent_sees_linked_child_in_students_list(self, roles, wire_permissions, student, other_student):
        parent_user = _user(roles["Parent"], "parent@example.com")
        guardian = Guardian.objects.create(user=parent_user, name="Rakesh Patel", relationship="father")
        StudentGuardian.objects.create(student=student, guardian=guardian)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/students/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["admission_no"] == student.admission_no

    def test_parent_sees_linked_child_enrollment(self, roles, wire_permissions, student, other_student, class_section):
        parent_user = _user(roles["Parent"], "parent@example.com")
        guardian = Guardian.objects.create(user=parent_user, name="Rakesh Patel", relationship="father")
        StudentGuardian.objects.create(student=student, guardian=guardian)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/enrollments/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["student"] == student.id

    def test_parent_sees_linked_child_attendance_only(self, roles, wire_permissions, student, other_student, class_section):
        parent_user = _user(roles["Parent"], "parent@example.com")
        guardian = Guardian.objects.create(user=parent_user, name="Rakesh Patel", relationship="father")
        StudentGuardian.objects.create(student=student, guardian=guardian)
        AttendanceRecord.objects.create(student=student, class_section=class_section, date="2026-07-01", status="present")
        AttendanceRecord.objects.create(student=other_student, class_section=class_section, date="2026-07-01", status="absent")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/attendance/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["student"] == student.id

    def test_parent_sees_linked_child_marks_only(self, roles, wire_permissions, student, other_student, class_section):
        parent_user = _user(roles["Parent"], "parent@example.com")
        guardian = Guardian.objects.create(user=parent_user, name="Rakesh Patel", relationship="father")
        StudentGuardian.objects.create(student=student, guardian=guardian)
        exam = Exam.objects.create(academic_year=class_section.academic_year, code="UT1", name="Unit Test 1", start_date="2026-08-01", end_date="2026-08-05")
        from apps.academics.models import Subject

        subject = Subject.objects.create(name="Mathematics", code="MATH")
        exam_subject = ExamSubject.objects.create(exam=exam, class_section=class_section, subject=subject, max_marks=50)
        Mark.objects.create(student=student, exam_subject=exam_subject, marks_obtained=42)
        Mark.objects.create(student=other_student, exam_subject=exam_subject, marks_obtained=30)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/marks/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["student"] == student.id

    def test_parent_sees_linked_child_fee_invoice_only(self, roles, wire_permissions, student, other_student, class_section):
        parent_user = _user(roles["Parent"], "parent@example.com")
        guardian = Guardian.objects.create(user=parent_user, name="Rakesh Patel", relationship="father")
        StudentGuardian.objects.create(student=student, guardian=guardian)
        fee_structure = FeeStructure.objects.create(
            class_section=class_section, academic_year=class_section.academic_year, fee_head="Tuition", amount=10000, due_date="2026-07-01"
        )
        FeeInvoice.objects.create(student=student, fee_structure=fee_structure, amount_due=10000)
        FeeInvoice.objects.create(student=other_student, fee_structure=fee_structure, amount_due=10000)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/fee-invoices/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["student"] == student.id

    def test_parent_with_no_linked_children_sees_nothing(self, roles, wire_permissions, student):
        _user(roles["Parent"], "parent@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/students/")

        assert response.status_code == 200
        assert response.data["count"] == 0
