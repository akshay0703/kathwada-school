from rest_framework.permissions import BasePermission

from apps.accounts.models import RolePermission


class HasModulePermission(BasePermission):
    """
    Generic, data-driven permission check used by every domain app's viewsets.

    A view opts in by declaring:

        class MarksViewSet(viewsets.ModelViewSet):
            permission_classes = [HasModulePermission]
            module_key = "marks"
            permission_action_map = {
                "list": "view", "retrieve": "view",
                "create": "create", "update": "edit", "partial_update": "edit",
                "destroy": "delete",
            }

    IMPORTANT — do not name this attribute `action_map`: DRF's own
    `ViewSetMixin` sets an *instance* attribute called exactly `action_map`
    (an HTTP-method -> action-name dict, e.g. {"post": "create"}, assigned in
    `.as_view(actions)` by the router) which silently shadows a same-named
    class attribute. This class deliberately uses `permission_action_map` to
    avoid that collision — this was a real latent bug in an earlier version
    of this class, caught by apps/academics's tests (the first real ViewSet
    to exercise this code path; the Phase 0 stub endpoint was a plain
    APIView and never hit this branch at all). See
    docs/handoffs/phase-1.1-academic-years.md for the full story. (It
    briefly regressed again during a merge on 2026-08-31 and was restored
    here — see docs/handoffs/phase-1.2-2.1-foundation-fix.md.)

    Superusers (is_superuser=True) always pass — an escape hatch for the
    Admin role / initial setup, matching the "Admin: full access" row in every
    line of the approved permission matrix.

    Everyone else is checked against the RolePermission table for
    (request.user.role, view.module_key, resolved_action). Deny by default:
    if no module_key is declared, or the user has no role, or no matching
    row exists, access is denied. This is what makes 0.8's acceptance test
    ("Student gets 403 on a stub admin-only endpoint, Admin gets 200 on the
    same endpoint") pass, and is the same mechanism every future domain app
    reuses — no per-app bespoke permission logic needed.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True

        module_key = getattr(view, "module_key", None)
        if not module_key:
            return False  # deny by default — a view must explicitly declare its module

        # ViewSets: resolve via permission_action_map + DRF's self.action
        # (list/retrieve/create/...). Plain APIViews (e.g. a one-off stub/
        # report endpoint): declare `required_action` directly instead,
        # since they have no `.action` attribute at all.
        resolved_action = getattr(view, "required_action", None)
        if resolved_action is None:
            permission_action_map = getattr(view, "permission_action_map", {})
            resolved_action = permission_action_map.get(getattr(view, "action", None))
        if not resolved_action:
            return False

        role = request.user.role
        if role is None:
            return False

        return RolePermission.objects.filter(
            role=role, module__key=module_key, action=resolved_action
        ).exists()
