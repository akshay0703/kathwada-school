from .base import *  # noqa: F401,F403
from .base import STORAGES, env

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")  # must be explicitly set, no default in prod

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Render puts each deployed service on its own isolated "site" for cookie
# purposes, even though the ERP frontend (kathwada-erp.onrender.com) and this
# backend (kathwada-erp-backend.onrender.com) share the onrender.com parent
# domain — Render deliberately isolates customer subdomains this way. That
# makes every request from the frontend to this API genuinely cross-site, so
# the default SameSite=Lax (fine for local dev, where everything is
# localhost) silently drops the session cookie on the follow-up request after
# login. SameSite=None + Secure (already True above) is required for this
# topology, and remains correct later even once a real custom domain puts
# both apps under one shared parent domain.
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

# WhiteNoise: compressed, cache-busted static file serving directly from the
# Django process — Render has no separate nginx/static-file server, so this
# replaces that role. Requires `python manage.py collectstatic` at deploy
# time (see render.yaml / docs/deployment.md).
STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}

