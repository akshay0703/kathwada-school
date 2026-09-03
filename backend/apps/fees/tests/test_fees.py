import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, ClassSection, SchoolClass, Section
from apps.accounts.models import Module, PermissionAction, Role, RolePermission, User
from apps.fees.models import FeeInvoice, FeePayment, FeeStructure
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
def fees_module(db):
    return Module.objects.create(key="fees", label="Fees")


@pytest.fixture
def wire_permissions(db, roles, fees_module):
    """Mirrors the real seeded matrix (apps/accounts/management/commands/seed_permissions.py)."""
    matrix = {
        "Admin": [V, C, E, D, X],
        "Principal": [V, X],
        # Teacher intentionally gets no rows at all — matches "Teacher": [].
        "Staff": [V, C, E, X],
        "Student": [V],
        "Parent": [V, X],
    }
    for role_name, actions in matrix.items():
        for action in actions:
            RolePermission.objects.create(role=roles[role_name], module=fees_module, action=action)


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
def fee_structure(db, class_section):
    return FeeStructure.objects.create(
        class_section=class_section,
        academic_year=class_section.academic_year,
        fee_head="Tuition",
        amount=10000,
        due_date="2026-07-01",
    )


@pytest.fixture
def student(db):
    return Student.objects.create(admission_no="KHS-2026-0001", first_name="Aarav", last_name="Patel", dob="2012-05-14")


@pytest.mark.django_db
class TestFeeStructurePermissions:
    def test_admin_can_create_fee_structure(self, roles, wire_permissions, class_section):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/fee-structures/",
            {"class_section": class_section.id, "academic_year": class_section.academic_year.id, "fee_head": "Tuition", "amount": "10000", "due_date": "2026-07-01"},
            format="json",
        )

        assert response.status_code == 201

    def test_teacher_has_no_access(self, roles, wire_permissions, fee_structure):
        """Fees matrix row: Teacher gets no rows at all."""
        _user(roles["Teacher"], "teacher@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "teacher@example.com")

        response = client.get("/api/v1/fee-structures/")

        assert response.status_code == 403

    def test_principal_cannot_create(self, roles, wire_permissions, class_section):
        """Fees matrix row: Principal has V,X — no Create."""
        _user(roles["Principal"], "principal@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "principal@example.com")

        response = client.post(
            "/api/v1/fee-structures/",
            {"class_section": class_section.id, "academic_year": class_section.academic_year.id, "fee_head": "Tuition", "amount": "10000", "due_date": "2026-07-01"},
            format="json",
        )

        assert response.status_code == 403

    def test_duplicate_fee_head_per_class_section_rejected(self, roles, wire_permissions, class_section, fee_structure):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/fee-structures/",
            {"class_section": class_section.id, "academic_year": class_section.academic_year.id, "fee_head": "Tuition", "amount": "12000", "due_date": "2026-08-01"},
            format="json",
        )

        assert response.status_code == 400

    def test_soft_delete_preserves_row(self, roles, wire_permissions, fee_structure):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/fee-structures/{fee_structure.id}/")

        assert response.status_code == 204
        assert FeeStructure.objects.filter(pk=fee_structure.pk).count() == 0
        assert FeeStructure.all_with_deleted.filter(pk=fee_structure.pk, deleted_at__isnull=False).count() == 1


@pytest.mark.django_db
class TestFeeInvoice:
    def test_admin_can_create_invoice_defaults_amount_due(self, roles, wire_permissions, fee_structure, student):
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/fee-invoices/",
            {"student": student.id, "fee_structure": fee_structure.id},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["amount_due"] == "10000.00"
        assert response.data["status"] == "pending"

    def test_duplicate_invoice_rejected(self, roles, wire_permissions, fee_structure, student):
        FeeInvoice.objects.create(student=student, fee_structure=fee_structure, amount_due=10000)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/fee-invoices/",
            {"student": student.id, "fee_structure": fee_structure.id},
            format="json",
        )

        assert response.status_code == 400

    def test_student_sees_only_own_invoices(self, roles, wire_permissions, fee_structure, student):
        other_student = Student.objects.create(admission_no="KHS-2026-0002", first_name="Diya", last_name="Shah", dob="2012-01-01")
        own_user = _user(roles["Student"], "student@example.com")
        student.user = own_user
        student.save()
        FeeInvoice.objects.create(student=student, fee_structure=fee_structure, amount_due=10000)
        FeeInvoice.objects.create(student=other_student, fee_structure=fee_structure, amount_due=10000)
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "student@example.com")

        response = client.get("/api/v1/fee-invoices/")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["student"] == student.id

    def test_parent_gets_empty_queryset(self, roles, wire_permissions, fee_structure, student):
        FeeInvoice.objects.create(student=student, fee_structure=fee_structure, amount_due=10000)
        _user(roles["Parent"], "parent@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "parent@example.com")

        response = client.get("/api/v1/fee-invoices/")

        assert response.status_code == 200
        assert response.data["count"] == 0


@pytest.mark.django_db
class TestFeePayment:
    def test_partial_payment_sets_status_partial(self, roles, wire_permissions, fee_structure, student):
        invoice = FeeInvoice.objects.create(student=student, fee_structure=fee_structure, amount_due=10000)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/fee-payments/",
            {"fee_invoice": invoice.id, "amount": "4000", "paid_at": "2026-07-05", "method": "cash"},
            format="json",
        )
        invoice.refresh_from_db()

        assert response.status_code == 201
        assert invoice.status == "partial"

    def test_full_payment_sets_status_paid(self, roles, wire_permissions, fee_structure, student):
        invoice = FeeInvoice.objects.create(student=student, fee_structure=fee_structure, amount_due=10000)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        client.post(
            "/api/v1/fee-payments/",
            {"fee_invoice": invoice.id, "amount": "10000", "paid_at": "2026-07-05", "method": "cash"},
            format="json",
        )
        invoice.refresh_from_db()

        assert invoice.status == "paid"

    def test_overpayment_rejected(self, roles, wire_permissions, fee_structure, student):
        invoice = FeeInvoice.objects.create(student=student, fee_structure=fee_structure, amount_due=10000)
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/fee-payments/",
            {"fee_invoice": invoice.id, "amount": "15000", "paid_at": "2026-07-05", "method": "cash"},
            format="json",
        )

        assert response.status_code == 400

    def test_second_payment_over_remaining_balance_rejected(self, roles, wire_permissions, fee_structure, student):
        invoice = FeeInvoice.objects.create(student=student, fee_structure=fee_structure, amount_due=10000)
        FeePayment.objects.create(fee_invoice=invoice, amount=7000, paid_at="2026-07-01")
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.post(
            "/api/v1/fee-payments/",
            {"fee_invoice": invoice.id, "amount": "4000", "paid_at": "2026-07-05", "method": "cash"},
            format="json",
        )

        assert response.status_code == 400

    def test_staff_can_record_payment_but_not_delete(self, roles, wire_permissions, fee_structure, student):
        invoice = FeeInvoice.objects.create(student=student, fee_structure=fee_structure, amount_due=10000)
        _user(roles["Staff"], "staff@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "staff@example.com")

        create_response = client.post(
            "/api/v1/fee-payments/",
            {"fee_invoice": invoice.id, "amount": "4000", "paid_at": "2026-07-05", "method": "cash"},
            format="json",
        )
        delete_response = client.delete(f"/api/v1/fee-payments/{create_response.data['id']}/")

        assert create_response.status_code == 201
        assert delete_response.status_code == 403

    def test_soft_delete_payment_recomputes_invoice_status(self, roles, wire_permissions, fee_structure, student):
        invoice = FeeInvoice.objects.create(student=student, fee_structure=fee_structure, amount_due=10000)
        payment = FeePayment.objects.create(fee_invoice=invoice, amount=10000, paid_at="2026-07-01")
        invoice.recompute_status()
        assert invoice.status == "paid"
        _user(roles["Admin"], "admin@example.com")
        client = APIClient(enforce_csrf_checks=False)
        _login(client, "admin@example.com")

        response = client.delete(f"/api/v1/fee-payments/{payment.id}/")
        invoice.refresh_from_db()

        assert response.status_code == 204
        assert invoice.status == "pending"
        assert FeePayment.all_with_deleted.filter(pk=payment.pk, deleted_at__isnull=False).count() == 1
