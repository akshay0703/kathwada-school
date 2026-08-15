class AuditLogMiddleware:
    """
    Lightweight request-level audit trail: every non-GET request to /api/ is
    logged with who did it, what endpoint, and the resulting status code.
    This is intentionally separate from the entity-level before/after diff
    logging that Phase 1 domain apps add via signals — this middleware alone
    already answers "who called what, when" even before any domain models
    exist, which is what Phase 0 needs to prove the AuditLog plumbing works.
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith("/api/") and request.method not in self.SAFE_METHODS:
            self._log(request, response)

        return response

    def _log(self, request, response):
        # Local import: avoids touching Django's app registry before it's ready
        # (middleware classes are imported at settings-load time).
        from apps.audit.models import AuditLog

        actor = getattr(request, "user", None)
        if actor is not None and not getattr(actor, "is_authenticated", False):
            actor = None

        try:
            AuditLog.objects.create(
                actor=actor,
                action="request",
                path=request.path,
                method=request.method,
                status_code=response.status_code,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except Exception:
            # Never let audit logging break the actual request/response cycle
            # (e.g. before migrations have run). Swallow and move on.
            pass
