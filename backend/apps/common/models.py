from django.db import models


class TimeStampedModel(models.Model):
    """Adds created_at/updated_at to any model that inherits it."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """Default manager excludes soft-deleted rows — use `all_with_deleted`
    on the model for admin/audit views that need to see everything."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    """
    Production replacement for the prototype's irreversible hard delete
    (see architecture doc §17 / §Part 2). `deleted_at` is set instead of the
    row being removed, so records stay in the audit trail and can be restored.
    """

    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_with_deleted = models.Manager()  # noqa: DJ012 — ruff's manager-ordering heuristic misfires on two managers in a row

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone

        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])
