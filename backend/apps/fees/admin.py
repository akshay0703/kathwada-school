from django.contrib import admin

from apps.fees.models import FeeInvoice, FeePayment, FeeStructure


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ["class_section", "fee_head", "amount", "due_date", "academic_year", "deleted_at"]
    list_filter = ["academic_year", "fee_head"]
    search_fields = ["fee_head"]


class FeePaymentInline(admin.TabularInline):
    model = FeePayment
    extra = 0


@admin.register(FeeInvoice)
class FeeInvoiceAdmin(admin.ModelAdmin):
    list_display = ["student", "fee_structure", "amount_due", "status", "deleted_at"]
    list_filter = ["status", "fee_structure__academic_year"]
    search_fields = ["student__admission_no", "student__first_name", "student__last_name"]
    inlines = [FeePaymentInline]


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ["fee_invoice", "amount", "paid_at", "method", "recorded_by", "deleted_at"]
    list_filter = ["method"]
