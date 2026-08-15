from rest_framework import serializers

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = ["id", "email", "role", "is_active", "is_superuser", "last_login_at"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
