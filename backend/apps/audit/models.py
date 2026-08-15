from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Matches the AuditLog entity in architecture doc §3.2. Phase 0 populates
    request-level rows (who hit which endpoint, when, what status came back)
    via the middleware. Phase 1 domain apps additionally write entity-level
    rows with before/after JSON diffs on Create/Update/Delete/Publish/Export
    of a specific model instance (entity_type/entity_id/before_json/after_json
    below already support that — no schema change needed later).
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    action = models.CharField(max_length=20)  # create/update/delete/publish/export/request
    entity_type = models.CharField(max_length=100, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    before_json = models.JSONField(null=True, blank=True)
    after_json = models.JSONField(null=True, blank=True)
    path = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=10, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} · {self.actor} · {self.action} {self.entity_type}"
