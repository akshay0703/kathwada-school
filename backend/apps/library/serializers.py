from rest_framework import serializers

from apps.library.models import Book, BookIssue


class BookSerializer(serializers.ModelSerializer):
    available_copies = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ["id", "title", "author", "category", "total_copies", "available_copies", "created_at", "updated_at"]
        read_only_fields = ["id", "available_copies", "created_at", "updated_at"]

    def get_available_copies(self, obj):
        return obj.available_copies()


class BookIssueSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    student_admission_no = serializers.CharField(source="student.admission_no", read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = BookIssue
        fields = [
            "id",
            "book",
            "book_title",
            "student",
            "student_name",
            "student_admission_no",
            "issue_date",
            "due_date",
            "return_date",
            "fine_amount",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "book_title", "student_name", "student_admission_no", "fine_amount", "is_overdue", "created_at", "updated_at"]
        extra_kwargs = {"due_date": {"required": False}}

    def get_is_overdue(self, obj):
        from datetime import date

        if obj.return_date:
            return obj.return_date > obj.due_date
        return date.today() > obj.due_date

    def validate(self, attrs):
        book = attrs.get("book", getattr(self.instance, "book", None))
        student = attrs.get("student", getattr(self.instance, "student", None))
        return_date = attrs.get("return_date", getattr(self.instance, "return_date", None))
        issue_date = attrs.get("issue_date", getattr(self.instance, "issue_date", None))

        if not self.instance and book:
            if book.available_copies() <= 0:
                raise serializers.ValidationError({"book": [f"No available copies of '{book.title}' to issue."]})

        if not self.instance and book and student:
            already_on_loan = BookIssue.objects.filter(book=book, student=student, return_date__isnull=True).exists()
            if already_on_loan:
                raise serializers.ValidationError(
                    {"non_field_errors": [f"{student.full_name} already has an unreturned copy of '{book.title}'."]}
                )

        if return_date and issue_date and return_date < issue_date:
            raise serializers.ValidationError({"return_date": ["Return date cannot be before the issue date."]})

        return attrs
