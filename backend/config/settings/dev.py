from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "backend"])

# In the Docker Compose dev stack, DATABASE_URL always points at the Postgres
# service (see docker/docker-compose.yml) — the approved architecture's DB is
# Postgres 16, unconditionally.
#
# NOTE (transparency, not an architecture change): this project was partly
# authored and smoke-tested inside a sandboxed environment with no Docker
# daemon and no Postgres server available. In that sandbox ONLY, tests were
# run with DATABASE_URL overridden to sqlite at the shell/environment level
# (never committed here) so migrations and the test suite could be verified
# end-to-end. Every checked-in default below still points at Postgres. See
# docs/architecture.md and the Phase 0 report for exactly which commands were
# run against sqlite vs. what still needs verification against real Postgres
# via `docker compose up`.

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://localhost:3001"],
)
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:3000", "http://localhost:3001"],
)

SESSION_COOKIE_SECURE = False  # local http only
CSRF_COOKIE_SECURE = False

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
