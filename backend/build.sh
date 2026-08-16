#!/usr/bin/env bash
# Runs on Render at every deploy. Do not run this yourself manually —
# Render calls it automatically per render.yaml's buildCommand.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate
python manage.py seed_permissions
python manage.py create_admin_from_env
