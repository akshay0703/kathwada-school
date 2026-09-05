from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Role, User
from apps.accounts.permissions import HasModulePermission
from apps.accounts.serializers import (
    LoginSerializer,
    RoleSerializer,
    SetPasswordSerializer,
    UserManagementSerializer,
    UserSerializer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    """
    GET /api/v1/auth/csrf/
    Frontend calls this once on load to receive the csrftoken cookie, then
    echoes its value back in the X-CSRFToken header on every unsafe request
    (POST/PUT/PATCH/DELETE) — standard Django double-submit-cookie CSRF flow,
    required because we use HttpOnly session cookies, not a bearer token.
    """
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    POST /api/v1/auth/login/  {"email": "...", "password": "..."}
    On success: sets an HttpOnly session cookie and returns the user profile.
    On failure: 401, generic message (never reveals whether the email exists).
    Never trusts a role/permission claim from the request body — role comes
    only from the User row looked up server-side.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = authenticate(
        request,
        username=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
    )
    if user is None or not user.is_active:
        return Response({"detail": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    user.last_login_at = timezone.now()
    user.save(update_fields=["last_login_at"])

    return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """POST /api/v1/auth/logout/ — clears the session server-side."""
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    GET /api/v1/auth/me/ — returns the current authenticated user.
    Returns 403 (not 401) for anonymous requests — this is DRF's documented
    SessionAuthentication behavior (no WWW-Authenticate challenge scheme is
    configured), not a bug.
    """
    return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """
    /api/v1/users/ — User & Role Management. Permissions per the "users"
    matrix row (apps/accounts/management/commands/seed_permissions.py):
    Admin VCEDX, every other role gets zero RolePermission rows on this
    module at all — this is intentionally the strictest module in the
    system, since it governs who can log in and as whom.

    Replaces AdminOnlyStubView (Phase 0 scaffolding, explicitly documented
    there as temporary "until a real admin-only endpoint exists" — this is
    that endpoint).

    No delete: User has no soft-delete mixin (unlike the domain profile
    models), and the task calls for activate/deactivate, not deletion — a
    generic PATCH to `is_active` covers that without inventing new
    deletion semantics on the auth table itself. Blocked two ways: `destroy`
    isn't in permission_action_map at all (so HasModulePermission denies it
    with 403 before DRF even looks up a handler), and `http_method_names`
    excludes DELETE outright as a second, independent layer.
    """

    queryset = User.objects.select_related("role").all().order_by("email")
    serializer_class = UserManagementSerializer
    permission_classes = [HasModulePermission]
    module_key = "users"
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    permission_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "set_password": "edit",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(email__icontains=search)
        role_id = self.request.query_params.get("role")
        if role_id:
            qs = qs.filter(role_id=role_id)
        is_active = self.request.query_params.get("is_active")
        if is_active in ("true", "false"):
            qs = qs.filter(is_active=(is_active == "true"))
        return qs

    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        """
        POST /api/v1/users/{id}/set-password/  {"password": "..."}
        The only way to change a user's password from this API — see
        SetPasswordSerializer's docstring for why this is a dedicated
        action rather than a PATCH field. Never returns the password.
        """
        user = self.get_object()
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    /api/v1/roles/ — read-only list of the six roles, for populating the
    "assign role" dropdown in the User Management UI. Same "users" module
    permissions as UserViewSet (Admin-only) — roles themselves are part of
    user/role management, not a separate module in the approved matrix.
    """

    queryset = Role.objects.all().order_by("name")
    serializer_class = RoleSerializer
    permission_classes = [HasModulePermission]
    module_key = "users"
    permission_action_map = {"list": "view", "retrieve": "view"}
