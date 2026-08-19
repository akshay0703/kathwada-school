from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Module, PermissionAction, Role, RolePermission

# Module registry — one row per line of the permission matrix in
# architecture doc §3.3. Domain apps built in later phases reference these
# keys from their viewsets' `module_key` attribute (see accounts/permissions.py).
MODULES = {
    "students": "Students",
    "guardians": "Guardians",
    "teachers": "Teachers",
    "classes_sections": "Classes / Sections",
    "subjects": "Subjects",
    "academic_years": "Academic Years",
    "exams": "Exams & Exam Components",
    "marks": "Marks Entry",
    "attendance": "Attendance",
    "fees": "Fees",
    "library": "Library",
    "documents": "Documents",
    "report_cards": "Report Cards",
    "audit_logs": "Audit Logs",
    "users": "Users & Role Management",
    "website_cms": "Public Website Content",
}

V, C, E, D, P, X = (
    PermissionAction.VIEW,
    PermissionAction.CREATE,
    PermissionAction.EDIT,
    PermissionAction.DELETE,
    PermissionAction.PUBLISH,
    PermissionAction.EXPORT,
)

# module_key -> role_name -> [actions]
# Transcribed directly from architecture doc §3.3. Note: qualifiers like
# "Teacher: V (own class only)" are NOT expressible in this flat matrix by
# design — that scoping is enforced by queryset filtering in each Phase 1
# domain app (e.g. via TeacherAssignment), not by this table. This table only
# answers "can this role do this action on this module at all".
MATRIX = {
    "students": {
        "Admin": [V, C, E, D, X], "Principal": [V, C, E, X], "Teacher": [V],
        "Staff": [V, C, E, X], "Student": [V], "Parent": [V],
    },
    "guardians": {
        "Admin": [V, C, E, D, X], "Principal": [V, E, X], "Teacher": [V],
        "Staff": [V, C, E, X], "Student": [], "Parent": [V, E],
    },
    "teachers": {
        "Admin": [V, C, E, D, X], "Principal": [V, E, X], "Teacher": [V, E],
        "Staff": [V], "Student": [], "Parent": [],
    },
    "classes_sections": {
        "Admin": [V, C, E, D, X], "Principal": [V, C, E, X], "Teacher": [V],
        "Staff": [V, X], "Student": [V], "Parent": [V],
    },
    "subjects": {
        "Admin": [V, C, E, D, X], "Principal": [V, E, X], "Teacher": [V],
        "Staff": [V], "Student": [V], "Parent": [V],
    },
    "academic_years": {
        # Principal: Create+Edit added in Phase 1.1 per explicit instruction
        # (was View+Export only). Delete deliberately stays Admin-only,
        # matching the pattern used for nearly every other module in this
        # matrix (Principal generally lacks Delete) and because Academic
        # Years are foundational, historical data — see
        # docs/handoffs/phase-1.1-academic-years.md for the full reasoning.
        "Admin": [V, C, E, D, X], "Principal": [V, C, E, X], "Teacher": [V],
        "Staff": [V], "Student": [V], "Parent": [V],
    },
    "exams": {
        "Admin": [V, C, E, D, X], "Principal": [V, C, E, X], "Teacher": [V],
        "Staff": [V], "Student": [V], "Parent": [V],
    },
    "marks": {
        "Admin": [V, C, E, D, X], "Principal": [V, E], "Teacher": [V, C, E],
        "Staff": [], "Student": [V], "Parent": [V],
    },
    "attendance": {
        "Admin": [V, C, E, D, X], "Principal": [V, E], "Teacher": [V, C, E],
        "Staff": [V, C], "Student": [V], "Parent": [V],
    },
    "fees": {
        "Admin": [V, C, E, D, X], "Principal": [V, X], "Teacher": [],
        "Staff": [V, C, E, X], "Student": [V], "Parent": [V, X],
    },
    "library": {
        "Admin": [V, C, E, D, X], "Principal": [V, X], "Teacher": [V, C],
        "Staff": [V, C, E, D, X], "Student": [V], "Parent": [V],
    },
    "documents": {
        "Admin": [V, C, E, D, X], "Principal": [V, X], "Teacher": [V, C],
        "Staff": [V, C], "Student": [V], "Parent": [V],
    },
    "report_cards": {
        "Admin": [V, C, E, D, P, X], "Principal": [V, E, P, X], "Teacher": [V, C],
        "Staff": [V, X], "Student": [V], "Parent": [V, X],
    },
    "audit_logs": {
        "Admin": [V, X], "Principal": [V, X], "Teacher": [], "Staff": [], "Student": [], "Parent": [],
    },
    "users": {
        "Admin": [V, C, E, D, X], "Principal": [], "Teacher": [], "Staff": [], "Student": [], "Parent": [],
    },
    "website_cms": {
        "Admin": [V, C, E, D, P, X], "Principal": [V, E, P], "Teacher": [], "Staff": [], "Student": [], "Parent": [],
    },
}


class Command(BaseCommand):
    help = "Seed the six approved roles, the module registry, and the default RolePermission matrix (architecture doc §3.3)."

    @transaction.atomic
    def handle(self, *args, **options):
        role_objs = {}
        for name in ["Admin", "Principal", "Teacher", "Staff", "Student", "Parent"]:
            role, created = Role.objects.get_or_create(name=name)
            role_objs[name] = role
            self.stdout.write(f"{'Created' if created else 'Exists '} role: {name}")

        module_objs = {}
        for key, label in MODULES.items():
            module, created = Module.objects.get_or_create(key=key, defaults={"label": label})
            module_objs[key] = module
            self.stdout.write(f"{'Created' if created else 'Exists '} module: {key}")

        created_count = 0
        for module_key, roles in MATRIX.items():
            module = module_objs[module_key]
            for role_name, actions in roles.items():
                role = role_objs[role_name]
                for action in actions:
                    _, created = RolePermission.objects.get_or_create(role=role, module=module, action=action)
                    created_count += 1 if created else 0

        self.stdout.write(self.style.SUCCESS(
            f"Done. {len(role_objs)} roles, {len(module_objs)} modules, "
            f"{created_count} new permission rows created."
        ))
