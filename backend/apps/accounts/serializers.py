from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import Role, User


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = ["id", "email", "role", "is_active", "is_superuser", "last_login_at"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "description"]


class UserManagementSerializer(serializers.ModelSerializer):
    """
    Read/write serializer for /api/v1/users/ (User Management, Admin-only —
    see UserViewSet). Never accepts or returns a password field: creation
    requires the dedicated `password` write-only field below (validated with
    Django's standard AUTH_PASSWORD_VALIDATORS, same as the rest of the auth
    system), and changing an existing user's password is a separate,
    explicit action (`set_password`, see UserViewSet) — never a side effect
    of a generic PATCH. This mirrors the same "explicit action instead of an
    implicit side effect" pattern already used throughout this codebase
    (AcademicYear's mark-current, ClassSection's subject assignment,
    BookIssue's return action).
    """

    role_id = serializers.PrimaryKeyRelatedField(source="role", queryset=Role.objects.all(), required=False, allow_null=True)
    role = serializers.CharField(source="role.name", read_only=True, default=None)
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "email", "role", "role_id", "is_active", "is_superuser", "last_login_at", "password", "created_at"]
        read_only_fields = ["id", "role", "is_superuser", "last_login_at", "created_at"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if self.instance is None and "password" not in attrs:
            raise serializers.ValidationError({"password": ["This field is required when creating a user."]})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        # Password changes never go through here — see set_password action.
        validated_data.pop("password", None)
        return super().update(instance, validated_data)


class SetPasswordSerializer(serializers.Serializer):
    """
    Input for POST /api/v1/users/{id}/set-password/ — the only way to
    change a user's password from this API (besides the user's own future
    self-service flow, which doesn't exist yet). Deliberately its own
    endpoint, not a field on UserManagementSerializer's PATCH, so a
    password change is always an explicit, auditable action rather than an
    easy-to-miss side effect buried in a general profile edit.
    """

    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_password(self, value):
        validate_password(value)
        return value
