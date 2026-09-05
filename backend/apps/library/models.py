from datetime import timedelta
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel

DEFAULT_LOAN_PERIOD_DAYS = 14
FINE_PER_OVERDUE_DAY = Decimal("2.00")


class Book(TimeStampedModel, SoftDeleteModel):
    """
    A title in the library catalog — see docs/prototype-analysis.md
    Sec13/Sec17.2's field list: "books: [{ id, title, author, category,
    copies }]" and the Sec17.2 normalization note calling for
    "Book/BookCopy/BookIssue with due dates and fines."

    This MVP deliberately keeps `total_copies` as a plain count on Book
    rather than modeling individual `BookCopy` rows with their own
    barcodes/IDs — the prototype had no per-copy tracking at all, and full
    per-copy identity (accession numbers, condition tracking, etc.) is a
    real school-library feature but not one called for anywhere in the
    approved docs beyond "copies" as a count. `available_copies()` below
    reproduces the prototype's own formula (Sec13:
    "available = copies - count(issues where returnDate is null)"), just
    computed against real BookIssue rows instead of a flat array. The two
    concrete gaps the docs DO call out — due dates and fines — are fully
    implemented on `BookIssue`.

    Soft delete only, same historical-integrity reasoning as everywhere
    else in this codebase — a withdrawn title's issue history should stay
    intact and queryable.
    """

    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=100, blank=True)
    total_copies = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.author})" if self.author else self.title

    def available_copies(self):
        issued_out = self.issues.filter(return_date__isnull=True).count()
        return self.total_copies - issued_out


class BookIssue(TimeStampedModel, SoftDeleteModel):
    """
    One loan of a Book to a Student — see docs/prototype-analysis.md
    Sec13's "issues: [{ id, bookId, roll, issueDate, returnDate }]",
    upgraded per the Sec17.2 normalization note to reference a real
    Student (not a bare roll-number string) and to add `due_date` and
    `fine_amount`, which the prototype had neither of ("no due date, no
    fines, no reservations").

    `due_date` defaults to `issue_date + DEFAULT_LOAN_PERIOD_DAYS` if not
    given explicitly. `fine_amount` is computed automatically when
    `return_date` is set past `due_date` — `FINE_PER_OVERDUE_DAY` is a
    simple flat placeholder rate (not a school-configurable fee schedule;
    that level of configurability belongs to the Fees module if ever
    needed, out of scope for this MVP).

    Availability is enforced server-side at issue time (the prototype only
    disabled the UI dropdown once `available <= 0` — "a soft client-side
    check only", per Sec13) — this is the same kind of real integrity gap
    already closed for roll numbers/admission numbers elsewhere in this
    codebase.

    Soft delete only, same historical-integrity reasoning as everywhere
    else in this codebase.
    """

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="issues")
    student = models.ForeignKey("people.Student", on_delete=models.PROTECT, related_name="book_issues")
    issue_date = models.DateField()
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    fine_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-issue_date"]

    def __str__(self):
        status = "returned" if self.return_date else "on loan"
        return f"{self.book.title} — {self.student.full_name} ({status})"

    def save(self, *args, **kwargs):
        from django.utils.dateparse import parse_date

        # Field assignment doesn't coerce str -> date the way form.clean()
        # does, so normalize here defensively before comparing dates below
        # (this matters for both direct ORM .create()/.save() calls with
        # string kwargs, and for the return_book action's request payload).
        if isinstance(self.issue_date, str):
            self.issue_date = parse_date(self.issue_date)
        if isinstance(self.due_date, str):
            self.due_date = parse_date(self.due_date)
        if isinstance(self.return_date, str):
            self.return_date = parse_date(self.return_date)

        if not self.due_date and self.issue_date:
            self.due_date = self.issue_date + timedelta(days=DEFAULT_LOAN_PERIOD_DAYS)
        if self.return_date and self.due_date and self.return_date > self.due_date:
            overdue_days = (self.return_date - self.due_date).days
            self.fine_amount = FINE_PER_OVERDUE_DAY * overdue_days
        elif self.return_date:
            self.fine_amount = Decimal("0.00")
        super().save(*args, **kwargs)
