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
