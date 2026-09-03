from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel


class FeeInvoiceStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PARTIAL = "partial", "Partial"
    PAID = "paid", "Paid"


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    CHEQUE = "cheque", "Cheque"
    ONLINE = "online", "Online"
    CARD = "card", "Card"
    OTHER = "other", "Other"


class FeeStructure(TimeStampedModel, SoftDeleteModel):
    """
    Defines one fee line item for a class-section — see
    docs/database-schema.md's ERD (`CLASS_SECTION ||--o{ FEE_STRUCTURE`)
    and docs/prototype-analysis.md §17.2's exact field list: "FeeStructure —
    id, class_section_id, academic_year_id, fee_head (e.g. Tuition/
    Transport), amount, due_date."

    Both `class_section` and `academic_year` are stored explicitly per the
    documented ERD, even though `class_section.academic_year` already
    implies it — same "carries its own academic_year_id" pattern already
    used by AttendanceRecord/Mark elsewhere in this codebase (see
    docs/database-schema.md's note on why year-scoped rows keep their own
    FK rather than reaching through a relation for historical stability).

    `fee_head` is a free-text label (Tuition/Transport/Lab/etc.) rather than
    a fixed enum — schools vary these per their own fee schedule, and the
    prototype had zero fee heads at all (§12: "one flat number per
    student"), so there's no existing enum to reuse or narrow.

    Soft delete only, same historical-integrity reasoning as everywhere
    else in this codebase.
    """

    class_section = models.ForeignKey(
        "academics.ClassSection", on_delete=models.PROTECT, related_name="fee_structures"
    )
    academic_year = models.ForeignKey("academics.AcademicYear", on_delete=models.PROTECT, related_name="fee_structures")
    fee_head = models.CharField(max_length=100, help_text="e.g. 'Tuition', 'Transport', 'Lab'")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    due_date = models.DateField()

    class Meta:
        ordering = ["academic_year", "class_section", "fee_head"]
        constraints = [
            models.UniqueConstraint(fields=["class_section", "fee_head"], name="fees_unique_structure_per_class_section"),
        ]

    def __str__(self):
        return f"{self.class_section} — {self.fee_head} ({self.amount})"


class FeeInvoice(TimeStampedModel, SoftDeleteModel):
    """
    One student's bill against one FeeStructure line item — see
    docs/prototype-analysis.md §17.2: "FeeInvoice — id, student_id,
    fee_structure_id, amount_due, status."

    `status` is stored (per the documented field list) but is never set
    directly by a client — `recompute_status()` derives it from the sum of
    non-deleted FeePayments against this invoice and is called
    automatically after every payment create/update/delete (see
    FeePaymentViewSet), so it can't drift out of sync with the actual
    payment history. Thresholds match the prototype's own status logic
    exactly (prototype-analysis.md §12): PAID once the balance reaches
    zero, PARTIAL once something has been paid but a balance remains,
    PENDING otherwise — the same three states, just computed from real
    FeePayment rows instead of a flat `feeTotals`/`feePayments` pair.

    `amount_due` defaults to the FeeStructure's amount at creation time but
    is its own field (not just read through the FK) so a per-student
    adjustment (e.g. a partial waiver) can be recorded without altering the
    FeeStructure line item every other student in the class is billed
    against.

    Soft delete only, same historical-integrity reasoning as everywhere
    else in this codebase.
    """

    student = models.ForeignKey("people.Student", on_delete=models.PROTECT, related_name="fee_invoices")
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.PROTECT, related_name="invoices")
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    status = models.CharField(max_length=10, choices=FeeInvoiceStatus.choices, default=FeeInvoiceStatus.PENDING)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["student", "fee_structure"], name="fees_unique_invoice_per_student_structure"),
        ]

    def __str__(self):
        return f"{self.student.full_name} — {self.fee_structure.fee_head} ({self.status})"

    def total_paid(self):
        return self.payments.aggregate(total=models.Sum("amount"))["total"] or Decimal("0")

    def recompute_status(self):
        paid = self.total_paid()
        if paid <= 0:
            new_status = FeeInvoiceStatus.PENDING
        elif paid < self.amount_due:
            new_status = FeeInvoiceStatus.PARTIAL
        else:
            new_status = FeeInvoiceStatus.PAID
        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])


class FeePayment(TimeStampedModel, SoftDeleteModel):
    """
    One payment recorded against a FeeInvoice — see
    docs/prototype-analysis.md §17.2: "FeePayment — id, fee_invoice_id,
    amount, paid_at, method, recorded_by_id."

    A single invoice may receive multiple partial payments over time (the
    entire reason FeeInvoice.status has a PARTIAL state), so this is a
    proper one-to-many child row, not folded into FeeInvoice itself.

    Soft delete only — the same historical-integrity reasoning as
    everywhere else in this codebase, and specifically important here: a
    corrected/reversed payment must not simply vanish from the money trail.
    Recomputes the parent invoice's status after every create/update/
    soft-delete (see FeePaymentViewSet).
    """

    fee_invoice = models.ForeignKey(FeeInvoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    paid_at = models.DateField()
    method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    recorded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="fee_payments_recorded"
    )

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.fee_invoice} — {self.amount} on {self.paid_at}"
