from django.contrib import admin

from apps.library.models import Book, BookIssue


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "category", "total_copies", "deleted_at"]
    list_filter = ["category"]
    search_fields = ["title", "author"]


@admin.register(BookIssue)
class BookIssueAdmin(admin.ModelAdmin):
    list_display = ["book", "student", "issue_date", "due_date", "return_date", "fine_amount", "deleted_at"]
    list_filter = ["issue_date"]
    search_fields = ["book__title", "student__admission_no", "student__first_name", "student__last_name"]
