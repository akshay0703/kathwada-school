from rest_framework.permissions import BasePermission

from apps.accounts.models import RolePermission


class HasModulePermission(BasePermission):
    """
    Generic, data-driven permission check used by every domain app's viewsets.

    A view opts in by declaring:

        class MarksViewSet(viewsets.ModelViewSet):
            permission_classes = [HasModulePermission]
            module_key = "marks"
            action_map = {
                "list": "view", "retrieve": "view",
                "create": "create", "update": "edit", "partial_update": "edit",
                "destroy": "delete",
            }

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

        # ViewSets: resolve via action_map + DRF's self.action (list/retrieve/create/...).
        # Plain APIViews (e.g. a one-off stub/report endpoint): declare `required_action`
        # directly instead, since they have no `.action` attribute.
        resolved_action = getattr(view, "required_action", None)
        if resolved_action is None:
            action_map = getattr(view, "action_map", {})
            resolved_action = action_map.get(getattr(view, "action", None))
        if not resolved_action:
            return False

        role = request.user.role
        if role is None:
            return False

        return RolePermission.objects.filter(
            role=role, module__key=module_key, action=resolved_action
        ).exists()
