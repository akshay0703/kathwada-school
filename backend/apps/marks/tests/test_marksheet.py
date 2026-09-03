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
    matrix = {
        "Admin": [V, C, E, D, X],
        "Principal": [V, E],
        "Teacher": [V, C, E],
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
def academic_year(db):
    return AcademicYear.objects.create(label="2026-27", start_date="2026-06-01", end_date="2027-04-30")


@pytest.fixture
def class_section(db, academic_year):
    school_class = SchoolClass.objects.create(name="Std 10", order=10)
    section = Section.objects.create(name="A")
    return ClassSection.objects.create(school_class=school_class, section=section, academic_year=academic_year)


@pytest.fixture
def exam(db, academic_year):
    return Exam.objects.create(academic_year=academic_year, code="UT1", name="Unit Test 1", start_date="2026-08-01", end_date="2026-08-05")


@pytest.fixture
def enrolled_student(db, class_section):
    student = Student.objects.create(admission_no="KHS-2026-0001", first_name="Aarav", last_name="Patel", dob="2012-05-14")
    Enrollment.objects.create(student=student, class_section=class_section, roll_no=1)
    return student


@pytest.fixture
def two_subjects_configured(db, exam, class_section):
    math = Subject.objects.create(name="Mathematics", code="MATH")
    science = Subject.objects.create(name="Science", code="SCI")
    math_es = ExamSubject.objects.create(exam=exam, class_section=class_section, subject=math, max_marks=50, passing_marks=18)
    science_es = ExamSubject.objects.create(exam=exam, class_section=class_section, subject=science, max_marks=50, passing_marks=18)
    return math_es, science_es


@pytest.mark.django_db
class TestMarksheetCalculation:
    def test_marksheet_totals_and_percentage(self, roles, wire_permissions, exam, enrolled_student, two_subjects_configured):
        math_es, science_es = two_subjects_configured
        Mark.objects.create(student=enrolled_student, exam_subject=math_es, marks_obtained=40)
        Mark.objects.create(student=enrolled_student, exam_subject=science_es, marks_obtained=30)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={enrolled_student.id}&exam={exam.id}")

        assert response.status_code == 200
        data = response.data
        assert float(data["total_obtained"]) == 70
        assert float(data["total_max"]) == 100
        assert data["percentage"] == 70.0
        assert len(data["subjects"]) == 2
        assert data["all_marks_entered"] is True

    def test_marksheet_pass_when_all_above_threshold(self, roles, wire_permissions, exam, enrolled_student, two_subjects_configured):
        math_es, science_es = two_subjects_configured
        Mark.objects.create(student=enrolled_student, exam_subject=math_es, marks_obtained=40)
        Mark.objects.create(student=enrolled_student, exam_subject=science_es, marks_obtained=30)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={enrolled_student.id}&exam={exam.id}")

        assert response.data["overall_result"] == "pass"

    def test_marksheet_fail_when_below_threshold(self, roles, wire_permissions, exam, enrolled_student, two_subjects_configured):
        math_es, science_es = two_subjects_configured
        Mark.objects.create(student=enrolled_student, exam_subject=math_es, marks_obtained=10)  # below passing_marks=18
        Mark.objects.create(student=enrolled_student, exam_subject=science_es, marks_obtained=30)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={enrolled_student.id}&exam={exam.id}")

        assert response.data["overall_result"] == "fail"
        math_row = next(s for s in response.data["subjects"] if s["subject_code"] == "MATH")
        assert math_row["passed"] is False

    def test_marksheet_incomplete_result_is_none(self, roles, wire_permissions, exam, enrolled_student, two_subjects_configured):
        math_es, _science_es = two_subjects_configured
        Mark.objects.create(student=enrolled_student, exam_subject=math_es, marks_obtained=40)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={enrolled_student.id}&exam={exam.id}")

        assert response.data["all_marks_entered"] is False
        assert response.data["overall_result"] is None

    def test_marksheet_no_passing_rule_gives_no_overall_result(self, roles, wire_permissions, exam, class_section, enrolled_student):
        subject = Subject.objects.create(name="Art", code="ART")
        es = ExamSubject.objects.create(exam=exam, class_section=class_section, subject=subject, max_marks=50)  # no passing_marks
        Mark.objects.create(student=enrolled_student, exam_subject=es, marks_obtained=45)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={enrolled_student.id}&exam={exam.id}")

        assert response.data["overall_result"] is None
        assert response.data["subjects"][0]["passed"] is None

    def test_marksheet_missing_enrollment_returns_404(self, roles, wire_permissions, exam):
        outsider = Student.objects.create(admission_no="KHS-2026-9999", first_name="X", last_name="Y", dob="2012-01-01")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={outsider.id}&exam={exam.id}")

        assert response.status_code == 404


@pytest.mark.django_db
class TestMarksheetPermissions:
    def test_student_can_view_own_marksheet(self, roles, wire_permissions, exam, enrolled_student, two_subjects_configured):
        math_es, science_es = two_subjects_configured
        Mark.objects.create(student=enrolled_student, exam_subject=math_es, marks_obtained=40)
        own_user = _user(roles["Student"], "student@example.com")
        enrolled_student.user = own_user
        enrolled_student.save()
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={enrolled_student.id}&exam={exam.id}")

        assert response.status_code == 200

    def test_student_cannot_view_other_students_marksheet(self, roles, wire_permissions, exam, enrolled_student):
        other_user = _user(roles["Student"], "other_student@example.com")
        Student.objects.create(user=other_user, admission_no="KHS-2026-9999", first_name="X", last_name="Y", dob="2012-01-01")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "other_student@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={enrolled_student.id}&exam={exam.id}")

        assert response.status_code == 403

    def test_staff_has_no_access_to_marksheet(self, roles, wire_permissions, exam, enrolled_student):
        """Marks matrix row: Staff gets no rows at all — 403 at the module-permission layer."""
        _user(roles["Staff"], "staff@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "staff@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={enrolled_student.id}&exam={exam.id}")

        assert response.status_code == 403

    def test_teacher_without_assignment_denied(self, roles, wire_permissions, exam, enrolled_student):
        teacher_user = _user(roles["Teacher"], "teacher@example.com")
        Teacher.objects.create(user=teacher_user, first_name="Meera", last_name="Joshi")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={enrolled_student.id}&exam={exam.id}")

        assert response.status_code == 403

    def test_teacher_with_assignment_allowed(self, roles, wire_permissions, exam, class_section, enrolled_student, two_subjects_configured):
        math_es, _ = two_subjects_configured
        css = ClassSectionSubject.objects.create(class_section=class_section, subject=math_es.subject)
        teacher_user = _user(roles["Teacher"], "teacher@example.com")
        teacher = Teacher.objects.create(user=teacher_user, first_name="Meera", last_name="Joshi")
        TeacherAssignment.objects.create(teacher=teacher, class_section_subject=css)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.get(f"/api/v1/marks/marksheet/?student={enrolled_student.id}&exam={exam.id}")

        assert response.status_code == 200


@pytest.mark.django_db
class TestClassMarksheet:
    def test_admin_can_view_class_marksheet(self, roles, wire_permissions, exam, class_section, enrolled_student, two_subjects_configured):
        math_es, science_es = two_subjects_configured
        other_student = Student.objects.create(admission_no="KHS-2026-0002", first_name="Diya", last_name="Shah", dob="2012-01-01")
        Enrollment.objects.create(student=other_student, class_section=class_section, roll_no=2)
        Mark.objects.create(student=enrolled_student, exam_subject=math_es, marks_obtained=40)
        Mark.objects.create(student=enrolled_student, exam_subject=science_es, marks_obtained=30)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.get(f"/api/v1/marks/class-marksheet/?class_section={class_section.id}&exam={exam.id}")

        assert response.status_code == 200
        assert len(response.data) == 2

    def test_student_role_cannot_view_class_marksheet(self, roles, wire_permissions, exam, class_section, enrolled_student):
        own_user = _user(roles["Student"], "student@example.com")
        enrolled_student.user = own_user
        enrolled_student.save()
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get(f"/api/v1/marks/class-marksheet/?class_section={class_section.id}&exam={exam.id}")

        assert response.status_code == 403
