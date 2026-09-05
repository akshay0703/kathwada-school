#!/usr/bin/env bash
# Runs on Render at every deploy. Do not run this yourself manually —
# Render calls it automatically per render.yaml's buildCommand.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate

# Idempotent — safe on every deploy. Uses get_or_create throughout, so it
# never creates duplicate roles/modules/permission rows on repeat runs; it
# only fills in whatever is missing (e.g. a newly-added module_key). Without
# this, a fresh database has zero RolePermission rows and every non-superuser
# gets a blanket 403 from HasModulePermission until someone runs this by hand.
python manage.py seed_permissions

# Idempotent — safe on every deploy (see the command's own docstring for the
# full create/leave-as-is/opt-in-reset behavior). Without this, a fresh
# database has zero User rows at all and, since Render's free Web Service
# plan has no Shell access, there would be no way to log into the ERP or
# reach Django admin to create one — this is what actually makes a first
# deploy usable. DJANGO_SUPERUSER_EMAIL/PASSWORD are read directly from the
# environment (see render.yaml) and are never hardcoded here.
python manage.py create_admin_from_env
