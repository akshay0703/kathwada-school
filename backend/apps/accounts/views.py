from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasModulePermission
from apps.accounts.serializers import LoginSerializer, UserSerializer


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


class AdminOnlyStubView(APIView):
    """
    GET /api/v1/auth/admin-stub/
    Exists ONLY to prove the Role/Permission scaffold (0.8) works end-to-end
    before any real domain module exists: it requires `view` on the `users`
    module, which only the Admin role holds per the seeded matrix
    (see apps/accounts/management/commands/seed_permissions.py). This view
    (and this endpoint) will be deleted once a real admin-only endpoint
    exists in Phase 1 — it is scaffolding, not a permanent feature.
    """

    permission_classes = [HasModulePermission]
    module_key = "users"
    required_action = "view"

    def get(self, request):
        return Response({"detail": "You have Admin-level access."})
