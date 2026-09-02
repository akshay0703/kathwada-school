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
from apps.exams.models import Exam, ExamSubject
from apps.marks.models import Mark
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
def marks_module(db):
    return Module.objects.create(key="marks", label="Marks Entry")


@pytest.fixture
def wire_permissions(db, roles, marks_module):
    """Mirrors the real seeded matrix (apps/accounts/management/commands/seed_permissions.py)."""
    matrix = {
        "Admin": [V, C, E, D, X],
        "Principal": [V, E],
        "Teacher": [V, C, E],
        # Staff intentionally gets no rows at all — matches the "marks" row's "Staff": [].
        "Student": [V],
        "Parent": [V],
    }
    for role_name, actions in matrix.items():
        for action in actions:
            RolePermission.objects.create(role=roles[role_name], module=marks_module, action=action)


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
def exam_subject(db, class_section):
    exam = Exam.objects.create(
        academic_year=class_section.academic_year, code="UT1", name="Unit Test 1", start_date="2026-08-01", end_date="2026-08-05"
    )
    subject = Subject.objects.create(name="Mathematics", code="MATH")
    return ExamSubject.objects.create(exam=exam, class_section=class_section, subject=subject, max_marks=50)


@pytest.fixture
def enrolled_student(db, class_section):
    student = Student.objects.create(admission_no="KHS-2026-0001", first_name="Aarav", last_name="Patel", dob="2012-05-14")
    Enrollment.objects.create(student=student, class_section=class_section, roll_no=1)
    return student


@pytest.mark.django_db
class TestMarksPermissions:
    def test_admin_can_enter_marks(self, roles, wire_permissions, exam_subject, enrolled_student):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/marks/",
            {"student": enrolled_student.id, "exam_subject": exam_subject.id, "marks_obtained": "42.5"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["marks_obtained"] == "42.50"
        assert response.data["entered_by_email"] == "admin@example.com"

    def test_principal_cannot_create_marks(self, roles, wire_permissions, exam_subject, enrolled_student):
        """Marks matrix row: Principal has V,E — no Create."""
        _user(roles["Principal"], "principal@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "principal@example.com")

        response = client.post(
            "/api/v1/marks/",
            {"student": enrolled_student.id, "exam_subject": exam_subject.id, "marks_obtained": "42.5"},
            format="json",
        )

        assert response.status_code == 403

    def test_staff_has_no_access(self, roles, wire_permissions, exam_subject):
        """Marks matrix row: Staff gets no rows at all."""
        _user(roles["Staff"], "staff@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "staff@example.com")

        response = client.get("/api/v1/marks/")

        assert response.status_code == 403

    def test_student_sees_only_own_marks(self, roles, wire_permissions, class_section, exam_subject, enrolled_student):
        other_student = Student.objects.create(admission_no="KHS-2026-0002", first_name="Diya", last_name="Shah", dob="2012-01-01")
        Enrollment.objects.create(student=other_student, class_section=class_section, roll_no=2)
        own_user = _user(roles["Student"], "student@example.com")
        enrolled_student.user = own_user
        enrolled_student.save()
        Mark.objects.create(student=enrolled_student, exam_subject=exam_subject, marks_obtained=42)
        Mark.objects.create(student=other_student, exam_subject=exam_subject, marks_obtained=30)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get("/api/v1/marks/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["student"] == enrolled_student.id

    def test_parent_gets_empty_queryset(self, roles, wire_permissions, exam_subject, enrolled_student):
        Mark.objects.create(student=enrolled_student, exam_subject=exam_subject, marks_obtained=42)
        _user(roles["Parent"], "parent@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/marks/")

        assert response.status_code == 200
        assert response.data["count"] == 0


@pytest.mark.django_db
class TestMarksValidation:
    def test_marks_exceeding_max_rejected(self, roles, wire_permissions, exam_subject, enrolled_student):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/marks/",
            {"student": enrolled_student.id, "exam_subject": exam_subject.id, "marks_obtained": "999"},
            format="json",
        )

        assert response.status_code == 400
        assert "marks_obtained" in response.data

    def test_duplicate_mark_rejected(self, roles, wire_permissions, exam_subject, enrolled_student):
        Mark.objects.create(student=enrolled_student, exam_subject=exam_subject, marks_obtained=42)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/marks/",
            {"student": enrolled_student.id, "exam_subject": exam_subject.id, "marks_obtained": "10"},
            format="json",
        )

        assert response.status_code == 400

    def test_non_enrolled_student_rejected(self, roles, wire_permissions, exam_subject):
        outsider = Student.objects.create(admission_no="KHS-2026-9999", first_name="X", last_name="Y", dob="2012-01-01")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/marks/",
            {"student": outsider.id, "exam_subject": exam_subject.id, "marks_obtained": "10"},
            format="json",
        )

        assert response.status_code == 400

    def test_edit_updates_existing_mark(self, roles, wire_permissions, exam_subject, enrolled_student):
        mark = Mark.objects.create(student=enrolled_student, exam_subject=exam_subject, marks_obtained=42)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.patch(f"/api/v1/marks/{mark.id}/", {"marks_obtained": "45"}, format="json")

        assert response.status_code == 200
        assert response.data["marks_obtained"] == "45.00"

    def test_soft_delete_preserves_row(self, roles, wire_permissions, exam_subject, enrolled_student):
        mark = Mark.objects.create(student=enrolled_student, exam_subject=exam_subject, marks_obtained=42)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/marks/{mark.id}/")

        assert response.status_code == 204
        assert Mark.objects.filter(pk=mark.pk).count() == 0
        assert Mark.all_with_deleted.filter(pk=mark.pk, deleted_at__isnull=False).count() == 1


@pytest.mark.django_db
class TestBulkSave:
    def test_bulk_save_creates_marks_for_all_students(self, roles, wire_permissions, class_section, exam_subject, enrolled_student):
        other_student = Student.objects.create(admission_no="KHS-2026-0002", first_name="Diya", last_name="Shah", dob="2012-01-01")
        Enrollment.objects.create(student=other_student, class_section=class_section, roll_no=2)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/marks/bulk-save/",
            {
                "exam_subject": exam_subject.id,
                "records": [
                    {"student": enrolled_student.id, "marks_obtained": "42"},
                    {"student": other_student.id, "marks_obtained": "38"},
                ],
            },
            format="json",
        )

        assert response.status_code == 201
        assert len(response.data) == 2
        assert Mark.objects.filter(exam_subject=exam_subject).count() == 2

    def test_bulk_save_rejects_over_max(self, roles, wire_permissions, exam_subject, enrolled_student):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/marks/bulk-save/",
            {"exam_subject": exam_subject.id, "records": [{"student": enrolled_student.id, "marks_obtained": "999"}]},
            format="json",
        )

        assert response.status_code == 400

    def test_bulk_save_is_idempotent_correction(self, roles, wire_permissions, exam_subject, enrolled_student):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")
        client.post(
            "/api/v1/marks/bulk-save/",
            {"exam_subject": exam_subject.id, "records": [{"student": enrolled_student.id, "marks_obtained": "20"}]},
            format="json",
        )

        response = client.post(
            "/api/v1/marks/bulk-save/",
            {"exam_subject": exam_subject.id, "records": [{"student": enrolled_student.id, "marks_obtained": "35"}]},
            format="json",
        )

        assert response.status_code == 201
        assert Mark.objects.filter(student=enrolled_student, exam_subject=exam_subject).count() == 1
        assert Mark.objects.get(student=enrolled_student, exam_subject=exam_subject).marks_obtained == 35

    def test_teacher_can_only_bulk_save_assigned_class_section(self, roles, wire_permissions, class_section, exam_subject, enrolled_student):
        other_academic_year = AcademicYear.objects.create(label="2027-28", start_date="2027-06-01", end_date="2028-04-30")
        other_section = Section.objects.create(name="B")
        other_class_section = ClassSection.objects.create(
            school_class=class_section.school_class, section=other_section, academic_year=other_academic_year
        )
        other_subject = Subject.objects.create(name="Science", code="SCI")
        other_exam_subject = ExamSubject.objects.create(
            exam=exam_subject.exam, class_section=other_class_section, subject=other_subject, max_marks=50
        )

        css = ClassSectionSubject.objects.create(class_section=class_section, subject=exam_subject.subject)
        teacher_user = _user(roles["Teacher"], "teacher@example.com")
        teacher = Teacher.objects.create(user=teacher_user, first_name="Meera", last_name="Joshi")
        TeacherAssignment.objects.create(teacher=teacher, class_section_subject=css)

        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        allowed_response = client.post(
            "/api/v1/marks/bulk-save/",
            {"exam_subject": exam_subject.id, "records": [{"student": enrolled_student.id, "marks_obtained": "20"}]},
            format="json",
        )
        denied_response = client.post(
            "/api/v1/marks/bulk-save/",
            {"exam_subject": other_exam_subject.id, "records": []},
            format="json",
        )

        assert allowed_response.status_code == 201
        assert denied_response.status_code == 403
