from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from apps.common.models import TimeStampedModel


class Role(models.Model):
    """
    The six roles approved in the architecture doc (§3.3): Admin, Principal,
    Teacher, Staff, Student, Parent. Stored as data (not a Python enum) so new
    roles can be added later via the Django admin without a code change.
    """

    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Email-based auth table only. Profile data (name, phone, etc.) lives on the
    domain-specific profile models (Student/Teacher/Guardian/Staff) added in
    Phase 1, each with a nullable 1:1 to this table — see architecture doc
    §3.2. Keeping this table minimal is deliberate: not every Student
    necessarily has login access on day one.
    """

    email = models.EmailField(unique=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="users", null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Django-admin access only, distinct from the `Staff` Role
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Module(models.Model):
    """
    Registry of ERP modules (Students, Marks, Attendance, ...) matching the
    rows of the permission matrix in the architecture doc §3.3. New modules
    are added here as data, one row each, as each domain app is built.
    """

    key = models.SlugField(max_length=50, unique=True)
    label = models.CharField(max_length=100)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label


class PermissionAction(models.TextChoices):
    VIEW = "view", "View"
    CREATE = "create", "Create"
    EDIT = "edit", "Edit"
    DELETE = "delete", "Delete"
    PUBLISH = "publish", "Publish"
    EXPORT = "export", "Export"


class RolePermission(models.Model):
    """
    One row = "this Role may perform this Action on this Module".
    This is the entire permission matrix from architecture doc §3.3, stored as
    data. Adjusting who can do what later is an admin data change (add/remove
    rows), never a code change — this directly satisfies the requirement to
    make the permission system adjustable without rewriting the application.
    """

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="role_permissions")
    action = models.CharField(max_length=10, choices=PermissionAction.choices)

    class Meta:
        unique_together = ("role", "module", "action")

    def __str__(self):
        return f"{self.role.name} · {self.action} · {self.module.key}"
