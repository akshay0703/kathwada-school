from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    GET /api/v1/health/
    Unauthenticated by design (used by load balancers / uptime monitors).
    Confirms the app process is up AND the database connection is alive.
    """
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    status_payload = {"status": "ok" if db_ok else "degraded", "database": db_ok}
    return Response(status_payload, status=200 if db_ok else 503)
