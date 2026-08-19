"""
Base settings shared by every environment.
Never put environment-specific values (DEBUG, ALLOWED_HOSTS, secrets) here —
those belong in dev.py / prod.py, driven entirely by environment variables.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-secret-key-change-me")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
]

# Phase 0 wired up `accounts`, `common`, and `audit`. Phase 1.1 adds
# `academics` (AcademicYear only, so far — Class/Section/Subject land in
# later Phase 1.x increments). The remaining domain apps still exist as
# empty scaffolding and are intentionally NOT added here yet — they're added
# one at a time as each domain is actually implemented.
LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.audit",
    "apps.academics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditLogMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — PostgreSQL 16 per approved architecture.
# DATABASE_URL is required and always supplied via docker-compose / deployment
# env vars. See dev.py for the one documented local-sandbox exception.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://kathwada:kathwada@localhost:5432/kathwada"),
}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# I18N
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Kathwada High School ERP API",
    "DESCRIPTION": "REST API for the Kathwada High School ERP (/api/v1/).",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------------------
# Auth / session cookies
# HttpOnly, server-side session auth per approved architecture — never JWT
# stored in localStorage/sessionStorage.
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_ENGINE = "django.contrib.sessions.backends.db"
CSRF_COOKIE_HTTPONLY = False  # frontend JS must read this to echo it back in the X-CSRFToken header
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"

# ---------------------------------------------------------------------------
# CORS — the ERP frontend (erp.kathwadahighschool.edu.in) and public site call
# the API cross-subdomain with credentials attached.
# ---------------------------------------------------------------------------
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000", "http://localhost:3001"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:3000", "http://localhost:3001"])

# ---------------------------------------------------------------------------
# File storage — S3-compatible (MinIO locally, AWS S3 / equivalent in prod).
# ---------------------------------------------------------------------------
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="minioadmin")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="minioadmin")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="kathwada-documents")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="http://minio:9000")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_ADDRESSING_STYLE = "path"
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = True  # generate signed, time-limited URLs — no public bucket

# ---------------------------------------------------------------------------
# Roles — Phase 0 ships the fixed set approved in the architecture doc.
# The mapping of Role -> Permission is data (rows in the Permission table,
# see apps.accounts.models), NOT hardcoded in Python, specifically so it can
# be adjusted later without a code change/rewrite (per your requirement).
# ---------------------------------------------------------------------------
DEFAULT_ROLES = ["Admin", "Principal", "Teacher", "Staff", "Student", "Parent"]
