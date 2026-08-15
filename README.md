# Kathwada High School — ERP & Public Website

Monorepo for the Kathwada High School production system. See
[`docs/architecture.md`](docs/architecture.md) for the full approved
architecture (tech stack, ERD, permission matrix, folder structure).

**Status: Phase 0 (Foundations) complete.** No domain features (Students,
Marks, Attendance, Fees, Library, Report Cards) exist yet — those are Phase 1.

## Stack

- Frontend: Next.js (App Router) — two apps, `public-site` and `erp`, sharing
  a design-system package.
- Backend: Django + Django REST Framework, `/api/v1/` versioned.
- Database: PostgreSQL 16.
- Storage: S3-compatible (MinIO locally).
- Auth: server-side sessions, HttpOnly cookies.

## Run everything with Docker Compose (recommended)

```bash
cd docker
docker compose up --build
```

This brings up Postgres, MinIO, the Django backend, both Next.js apps, and an
nginx reverse proxy. Once healthy:

- Public website: http://localhost:8080/
- ERP (behind the nginx `erp.` vhost — add a hosts-file entry, or hit the app
  container directly): http://localhost:3001/
- API health check: http://localhost:8000/api/v1/health/
- MinIO console: http://localhost:9001/ (minioadmin / minioadmin)

> **Note:** this repository was partly built and tested in a sandboxed
> environment with no Docker daemon available. The Docker Compose stack
> itself has **not** been verified end-to-end by an actual `docker compose
> up` run — please run it and confirm. Every other piece listed as
> "automatically verified" in the Phase 0 report *was* actually executed.

Seed the roles/permissions and an admin user inside the running backend
container:

```bash
docker compose exec backend python manage.py seed_permissions
docker compose exec backend python manage.py createsuperuser
```

## Run manually (no Docker)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then point DATABASE_URL at a real Postgres instance
python manage.py migrate
python manage.py seed_permissions
python manage.py createsuperuser
python manage.py runserver
```

Run the backend test suite:

```bash
python -m pytest -v
ruff check .
```

### Frontend

```bash
cd frontend
npm install
npm run dev:public-site   # http://localhost:3000
npm run dev:erp           # http://localhost:3001
```

Build/lint (what CI runs):

```bash
npm run build
npm run lint
```

## Legacy data migration

See [`docs/migration/README.md`](docs/migration/README.md). Dry-run the
parser against the bundled demo fixture:

```bash
python scripts/import_legacy_localstorage.py scripts/sample_data/khs_erp_data_v1.demo.json
```

## Repository layout

See `docs/architecture.md` §3.4 for the full annotated folder structure.
