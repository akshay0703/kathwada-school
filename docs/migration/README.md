# Legacy prototype data migration

The old prototype (`kathwada-high-school.html`) stores everything in one
`localStorage` key: `khs_erp_data_v1`. The exact JSON shape is documented in
full in `docs/architecture.md` §15.

## Current status

No real (non-demo) student data has been provided yet (per your Phase 0
decision). The migration script therefore currently only **validates and
parses** an export — it does **not** write to any database.

## How to use it

1. In the browser where the prototype was actually used, open DevTools →
   Console, and run:
   ```js
   copy(localStorage.getItem("khs_erp_data_v1"))
   ```
   This copies the raw JSON to your clipboard. Paste it into a file, e.g.
   `real_export.json`.
2. Run the dry-run parser against it:
   ```bash
   python scripts/import_legacy_localstorage.py real_export.json
   ```
3. Review the printed report. It calls out:
   - How many students/teachers/books/attendance dates/fee records it found.
   - Whether any non-zero marks were actually entered (vs. an empty/demo
     instance).
   - Every validation issue found (duplicate roll numbers, non-numeric marks,
     missing names, etc.) — nothing is silently dropped or guessed.
4. If issues are reported, they need to be resolved (either by fixing the
   source data or by us jointly deciding how to handle each case) before any
   database-writing import logic is built.

## What happens next (not yet built)

Once you confirm real data exists and the dry-run report looks correct, the
next step (Phase 1, not Phase 0) is to extend this script with an actual
write path: creating `Student`, `Guardian`, `StudentGuardian`, `Mark`, etc.
rows via Django's ORM inside a single transaction, so a partial failure can't
leave the database half-migrated.
