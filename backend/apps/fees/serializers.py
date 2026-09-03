from rest_framework import serializers

from apps.fees.models import FeeInvoice, FeePayment, FeeStructure


class FeeStructureSerializer(serializers.ModelSerializer):
    school_class_name = serializers.CharField(source="class_section.school_class.name", read_only=True)
    section_name = serializers.CharField(source="class_section.section.name", read_only=True)
    academic_year_label = serializers.CharField(source="academic_year.label", read_only=True)

    class Meta:
        model = FeeStructure
        fields = [
            "id",
            "class_section",
            "school_class_name",
            "section_name",
            "academic_year",
            "academic_year_label",
            "fee_head",
            "amount",
            "due_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "school_class_name", "section_name", "academic_year_label", "created_at", "updated_at"]


class FeePaymentSerializer(serializers.ModelSerializer):
    recorded_by_email = serializers.CharField(source="recorded_by.email", read_only=True, default=None)

    class Meta:
        model = FeePayment
        fields = ["id", "fee_invoice", "amount", "paid_at", "method", "recorded_by", "recorded_by_email", "created_at"]
        read_only_fields = ["id", "recorded_by", "recorded_by_email", "created_at"]

    def validate(self, attrs):
        fee_invoice = attrs.get("fee_invoice", getattr(self.instance, "fee_invoice", None))
        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        if fee_invoice and amount is not None:
            already_paid = fee_invoice.total_paid()
            if self.instance:
                already_paid -= self.instance.amount
            if already_paid + amount > fee_invoice.amount_due:
                remaining = fee_invoice.amount_due - already_paid
                raise serializers.ValidationError(
                    {"amount": [f"This would exceed the amount due. At most {remaining} can still be paid on this invoice."]}
                )
        return attrs

    def create(self, validated_data):
        validated_data["recorded_by"] = self.context["request"].user
        payment = super().create(validated_data)
        payment.fee_invoice.recompute_status()
        return payment

    def update(self, instance, validated_data):
        payment = super().update(instance, validated_data)
        payment.fee_invoice.recompute_status()
        return payment


class FeeInvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_admission_no = serializers.CharField(source="student.admission_no", read_only=True)
    fee_head = serializers.CharField(source="fee_structure.fee_head", read_only=True)
    due_date = serializers.DateField(source="fee_structure.due_date", read_only=True)
    academic_year_label = serializers.CharField(source="fee_structure.academic_year.label", read_only=True)
    amount_paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    payments = FeePaymentSerializer(many=True, read_only=True)
    amount_due = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, help_text="Defaults to the fee structure's amount if omitted."
    )

    class Meta:
        model = FeeInvoice
        fields = [
            "id",
            "student",
            "student_name",
            "student_admission_no",
            "fee_structure",
            "fee_head",
            "due_date",
            "academic_year_label",
            "amount_due",
            "amount_paid",
            "balance",
            "status",
            "payments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_name",
            "student_admission_no",
            "fee_head",
            "due_date",
            "academic_year_label",
            "amount_paid",
            "balance",
            "status",
            "payments",
            "created_at",
            "updated_at",
        ]

    def get_amount_paid(self, obj):
        return obj.total_paid()

    def get_balance(self, obj):
        return obj.amount_due - obj.total_paid()

    def validate(self, attrs):
        student = attrs.get("student", getattr(self.instance, "student", None))
        fee_structure = attrs.get("fee_structure", getattr(self.instance, "fee_structure", None))
        if student and fee_structure:
            conflict = FeeInvoice.objects.filter(student=student, fee_structure=fee_structure)
            if self.instance:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": [f"An invoice already exists for {student.full_name} against this fee structure."]}
                )
        return attrs

    def create(self, validated_data):
        if not validated_data.get("amount_due"):
            validated_data["amount_due"] = validated_data["fee_structure"].amount
        return super().create(validated_data)


class FeeInvoiceListSerializer(serializers.ModelSerializer):
    """Lighter-weight list serializer, omitting the nested payments."""

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_admission_no = serializers.CharField(source="student.admission_no", read_only=True)
    fee_head = serializers.CharField(source="fee_structure.fee_head", read_only=True)
    amount_paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()

    class Meta:
        model = FeeInvoice
        fields = [
            "id",
            "student",
            "student_name",
            "student_admission_no",
            "fee_structure",
            "fee_head",
            "amount_due",
            "amount_paid",
            "balance",
            "status",
        ]

    def get_amount_paid(self, obj):
        return obj.total_paid()

    def get_balance(self, obj):
        return obj.amount_due - obj.total_paid()
