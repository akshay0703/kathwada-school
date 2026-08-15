# Kathwada High School — Prototype Analysis & Production Architecture

**Status:** Analysis + proposed architecture. **No code has been implemented.** Phase 0 begins only after you approve this document.

---

# PART 1 — PROTOTYPE ANALYSIS

Source: `kathwada-high-school.html` (single file, ~693KB). It contains:
- An **outer shell** — the public website (Home / About / Academics / Admissions / Gallery / News & Events / Contact) plus a login "gate" and a lazy-loaded iframe.
- An **inner app** — the actual ERP, stored **base64-encoded inside a JS string** (`ERP_HTML_B64`) and injected into the iframe's `srcdoc` only after login. I decoded this to inspect it directly.

Every claim below is taken directly from the code. Anything I could not determine is marked **UNKNOWN — REQUIRES CONFIRMATION**.

## 1. Data structure represented in JS / localStorage

The whole ERP runs on one in-memory JS object, `state`, periodically (every 2s, and on `beforeunload`) serialized to JSON and written to `localStorage`. There is **no backend and no database** — everything is client-side.

```js
const state = {
  school, addr, classLabel, year,      // single free-text strings, letterhead info
  teacher, principal,                   // free-text names, not linked to Teacher records
  subjects: [ "Gujarati", "English", ... ],  // flat array of strings — NOT an entity with IDs
  max:  { fst, sst, ut1, ut2, main },   // per-subject max marks for each test
  pass: { fst, sst, ut1, ut2, main },   // per-subject passing marks for each test
  internalMax: { p1, p2, p3 },          // max marks for the 3 internal-assessment parts
  internalPass,                          // combined passing mark for internal (out of p1+p2+p3)
  students: [ Student ],
  teachers: [ Teacher ],
  attendanceByDate: { [date]: { [roll]: "P"|"A" } },
  feeTotals: { [roll]: number },
  feePayments: [ { id, roll, amount, date } ],
  books: [ Book ],
  issues: [ Issue ],
  view / cardIdx / entryTab             // pure UI state, not business data
}
```

## 2. Student fields & relationships

```js
{ roll, name, marks: {}, cls, dob, guardian, guardianPhone, address }
```
- `roll` is an auto-incrementing integer assigned client-side (`nextRoll++`), but the **roll input field is plain text** — nothing prevents a user from editing it to a duplicate or non-numeric value. **No uniqueness validation exists.**
- `cls` is a free-text string that defaults to `state.classLabel` — it is **not a foreign key to any Class/Section entity** (none exists).
- `guardian` / `guardianPhone` are flat strings on the student record. **There is no separate Guardian/Parent entity** — a student can have exactly one guardian name and one phone number, no relationship table, no guardian login.
- `marks` is a nested object: `marks[subjectName][testKey] = "value"` for `fst/sst/ut1/ut2/main`, plus `marks[subjectName].internal = {p1,p2,p3}`.
- Deleting a student (`hardDeleteStudent`) cascades and removes their attendance entries, fee totals/payments, and library issues — but this is a **client-side hard delete with no audit trail**.

## 3. Class / section / subject structure

**This is the single biggest structural gap versus your requirements.** The prototype supports **exactly one class-section at a time** per browser tab:
- `state.classLabel` is one free-text string (e.g. `"Std 10 – A"`).
- `state.subjects` is one flat array of subject-name strings, shared by every student.
- There is **no Class entity, no Section entity, no Subject entity with an ID**, and **no way to manage two classes simultaneously** — running Std 9-A and Std 10-B would require two separate browser tabs/localStorage blobs with no relationship between them.
- Subject presets exist for convenience only: `"9-10"`, `"arts"`, `"commerce"` — hardcoded arrays, not stored/configurable beyond a comma-separated textarea.

**UNKNOWN — REQUIRES CONFIRMATION:** whether the production system should support the school running multiple simultaneous class-sections from one login (I assume yes, since your brief explicitly asks for Classes/Sections as ERD entities — but the prototype gives no guidance on the intended workflow for a school with many sections).

## 4. Exam types & components

Five fixed, **hardcoded** test slots (not stored as configurable data rows):
```js
const TESTS = [
  { key:"fst",  label:"First School Test" },
  { key:"sst",  label:"Second School Test" },
  { key:"ut1",  label:"Unit Test 1" },
  { key:"ut2",  label:"Unit Test 2" },
  { key:"main", label:"Main Exam" }
];
```
Plus a sixth, virtual "Internal Marks" component made of **three named sub-parts** (`p1`, `p2`, `p3` — UI labels them "Part 1 / Part 2 / Part 3", e.g. Home Assignment / Class Test / Project Work, but those labels are just placeholder text, not stored).

Each of FST/SST/UT1/UT2/Main has one global **max marks** and one global **passing marks**, applied identically to every subject. Internal has 3 part-level max-marks and **one combined passing mark** (not per-part).

There is no way to add a 6th exam type, rename an exam, or have different max/pass marks per subject — all of this is hardcoded in JS, not data-driven.

## 5. FST + SST + UT1 + UT2 + Internal + Main formula & weightages

This is the most important logic to preserve exactly. Three separate computations exist:

**A. Single-test computation** (`computeTest(testKey)`, used for FST/SST/UT1/UT2/Main individually):
- Per subject: `mark = num(student.marks[subject][testKey])`
- `total = Σ(marks across all subjects)`
- `maxTotal = maxPerSubject × numberOfSubjects`
- `pct = total / maxTotal × 100`
- **Result (pass/fail) for this test** = PASS only if **every single subject** scored ≥ the test's passing mark (`allPass` flag — a per-subject gate, not a total-marks gate).

**B. Internal Marks computation** (`computeInternal()`):
- Per subject: `subTotal = p1 + p2 + p3`
- `total = Σ(subTotal across subjects)`; `maxTotal = (p1max+p2max+p3max) × numSubjects`
- Subject fails internal if `subTotal < internalPass` (combined 3-part total vs one threshold — not evaluated per-part).

**C. Main Marksheet computation — the combined one** (`computeMain()`), this is the authoritative "FST+SST+UT1+UT2+Internal+Main" formula:
```
subjectMax     = max(fst) + max(sst) + max(ut1) + max(ut2) + max(main) + internalMaxTotal
subjectPassReq = pass(fst) + pass(sst) + pass(ut1) + pass(ut2) + pass(main) + internalPass

for each subject:
  subjectTotal = fst_mark + sst_mark + ut1_mark + ut2_mark + main_mark + (p1+p2+p3)
  subjectPct   = subjectTotal / subjectMax × 100
  subjectPass  = subjectTotal >= subjectPassReq      ← combined total vs combined threshold,
                                                          NOT "must pass every component separately"

overallTotal    = Σ(subjectTotal across all subjects)
overallMax      = subjectMax × numSubjects
overallPassReq  = subjectPassReq × numSubjects
overallPct      = overallTotal / overallMax × 100
finalResult     = PASS only if (every subject's subjectPass is true) AND (overallTotal >= overallPassReq)
```
**Important nuance:** passing a *subject* on the Main Marksheet does **not** require passing FST individually, SST individually, etc. — it only requires the **sum across all six components to clear the sum of their passing marks**. A student could theoretically fail one component badly and compensate with another. This is different from, and independent of, whether that student was separately marked "FAIL" on the FST-only or SST-only class register. **This distinction is a critical business rule to preserve exactly as-is** — please confirm this compensatory (aggregate) pass logic is intentional before I encode it, since it's easy to mistakenly "fix" this into a stricter per-component pass rule during rebuild.

Default weightages configured (editable in Setup, these are just the defaults):
| Component | Max | Pass |
|---|---|---|
| First School Test (FST) | 25 | 8 |
| Second School Test (SST) | 25 | 8 |
| Unit Test 1 (UT1) | 50 | 17 |
| Unit Test 2 (UT2) | 50 | 17 |
| Internal Marks (P1+P2+P3) | 5+5+10=20 | 7 |
| Main Exam | 80 (or 100 for Std 12 quick-set) | 26 (or 33) |
| **Subject Total** | **250** (or 270) | **83** (or 91) |

## 6. Grade boundaries

One shared `getGrade(pct)` function used everywhere (single test, internal, and combined main):
```
≥90 → A1   ≥80 → A2   ≥70 → B1   ≥60 → B2
≥50 → C1   ≥40 → C2   ≥33 → D    <33 → E
```
Grade is purely a **display label** derived from percentage — it does not affect pass/fail.

## 7. Pass/fail rules

Confirmed exactly as coded (see #5 above):
- **Per single test**: fail if ANY subject < that test's passing mark.
- **Internal**: fail if ANY subject's 3-part total < internalPass.
- **Main Marksheet (authoritative result)**: fail if ANY subject's 6-component combined total < combined passReq, OR the grand total < the grand passReq.
- No grace marks, no moderation, no supplementary/re-exam logic, no attendance-linked eligibility rule exists anywhere. **UNKNOWN — REQUIRES CONFIRMATION** if any of these should be added in production (they are not in the prototype, so I will not invent them).

## 8. Ranking & tie-handling logic

```js
function ranksFromValues(values){
  sort descending by value;
  if current value === previous value → same rank as previous;
  else → rank = position + 1;
}
```
This is **standard/competition ranking with ties sharing a rank and the next distinct rank skipping accordingly** (e.g., two students tied at 2nd both get rank 2, the next student gets rank 4, not 3). Ties are broken **purely by matching percentage** — there is **no secondary tiebreaker** (not by best subject, not alphabetical, not by roll number). Ranking is computed **independently for each view**: per single test, for Internal Marks, and for the combined Main Marksheet (three separate ranking runs, not one).

## 9. Internal-mark calculation / breakdown

Three parts per subject (`p1`, `p2`, `p3`), each with an independently configurable max (defaults 5/5/10 = 20 total). Entered as raw numbers (supports 0.5 step, i.e., half-marks). Combined total per subject shown live as you type. One single combined passing mark applies to the sum of all three parts (default 7), not to each part individually.

## 10. Report-card fields, layout, calculations, output

Three card types, all built from shared HTML builder functions (`letterheadHTML`, `signRowHTML`, `legendHTML`, `watermarkHTML`, `wrapSheet`, `sealSVG`):

- **`testCardHTML`** — single-test individual card (Subject / Max / Obtained / Grade / Result rows).
- **`internalCardHTML`** — internal-marks card (Subject / Part1 / Part2 / Part3 / Total / Grade / Result).
- **`reportCardHTML`** — the main combined report card. Columns: Subject, FST, SST, UT1, UT2, Main, Internal (each capped at its max), Total, %, Grade, Result. Footer summary box: Grand Total/Max, Percentage, Overall Grade, Class Rank.

Shared visual elements on every printed sheet:
- Letterhead: circular school crest (embedded base64 PNG), school name, address, document title, an "index box" (Roll No / Name / Class / Year).
- A rotated **PASS/FAIL "stamp"** top-right (green border for PASS, red for FAIL).
- A faint diagonal **watermark** ("KHS · KATHWADA") behind the content.
- Grade-legend footer strip.
- Signature row: auto-filled today's date, "Kathwada" as place, two signature lines (Class Teacher / Principal, falling back to those literal labels if the names aren't set).
- A decorative circular **seal** (SVG/embedded image) bottom-right.
- Print CSS forces **A4 landscape**, hides everything except `#printArea`, one sheet per page (`page-break-after: always`).

Class Registers (`buildTestRegisterBody`, `buildMainRegisterBody`, `buildInternalRegisterBody` + matching `print...Register` functions) are the tabular, all-students-at-once equivalent of the same data, also printable with the same letterhead/legend/signature treatment.

An **Excel export** (`exportToExcel`, via SheetJS/`xlsx.full.min.js` from a CDN) dumps one worksheet per test, one for Internal Marks, one for the Main Marksheet.

## 11. Attendance calculation logic

```js
attendanceByDate: { [dateString]: { [roll]: "P" | "A" } }
```
- Binary **Present/Absent only** — no Late/Half-day/Excused/Leave statuses.
- A date's record is created lazily; if a student has no entry yet for that date, the UI **displays** them as "P" by default but this is **not actually persisted** until a button is clicked — meaning an unmarked student looks identical to a marked-present student until you dig into the data.
- Attendance % is only ever computed **for the single date currently displayed** ("Present: X · Absent: Y · Z% attendance" footer) — there is **no cumulative per-student attendance percentage anywhere** (not for a month, term, or year). **UNKNOWN — REQUIRES CONFIRMATION**: your ERD asks for an "Attendance" module capable of real reporting — this needs to be designed from scratch, not migrated, since the prototype has no aggregate logic to preserve.

## 12. Fee calculation / status logic

```js
feeTotals:   { [roll]: totalFeeNumber }   // one flat number per student, no fee heads
feePayments: [ { id, roll, amount, date } ]  // flat transaction list, entered via a JS prompt()
```
- `paid = Σ(payments for that roll)`; `pending = max(total - paid, 0)`.
- Status: `"—"` if no fee set, `"PAID"` if pending=0, `"PARTIAL"` if paid>0 and pending>0, else `"PENDING"`.
- No fee structure by class/term, no fee heads (tuition/transport/etc.), no due dates, no discounts/scholarships, no printable receipts/invoices. This is the thinnest module in the prototype — production will be almost entirely new design, not migration.

## 13. Library data structure & logic

```js
books:  [ { id, title, author, category, copies } ]      // no ISBN, no per-copy tracking
issues: [ { id, bookId, roll, issueDate, returnDate } ]   // no due date, no fines, no reservations
```
`available = copies - count(issues where bookId matches and returnDate is null)`. Issuing is blocked in the UI once `available <= 0` (dropdown option disabled), but this is a soft client-side check only.

## 14. Existing users/roles/permissions represented in the prototype

This is the most important security finding:
- Login gate lives in the **outer shell**, not inside the ERP app itself: `const ERP_CREDENTIALS = { admin: "admin123", staff: "staff123" };` — **hardcoded, plaintext, visible in page source**, checked entirely client-side (`if(ERP_CREDENTIALS[u] === p)`).
- There is **no session, no token, no backend validation whatsoever** — once either password is typed in, `erpAuthed = true` is just a JS boolean and the full ERP iframe loads.
- **Both accounts are functionally identical** — there is no permission differentiation between "admin" and "staff" anywhere in the code. Every logged-in user can view/edit/delete every module.
- **No Teacher, Student, Parent, or Principal accounts/roles exist at all.** The Role-Permission Matrix you asked for (§3 below) has **no prototype precedent** — it must be designed fresh, guided by your stated requirements, not migrated.

## 15. localStorage keys & stored JSON shape

Only one key is used, and only by the **outer shell** (the ERP iframe never touches `localStorage` directly when embedded — it talks to the parent page via `postMessage`, which is the only reliable persistence path in that architecture; a standalone-file fallback exists too):

```
Key:   "khs_erp_data_v1"
Value: JSON string of buildPayload():
{
  school, addr, classLabel, year, teacher, principal, subjects,
  max, pass, internalMax, internalPass,
  students, teachers,
  attendanceByDate, feeTotals, feePayments,
  books, issues,
  counters: { nextRoll, nextTeacherId, nextBookId, nextIssueId, nextPaymentId }
}
```
This is exactly the shape needed for a migration/import script (see §Migration Strategy below). **In this chat, no actual saved data was provided** — the file you uploaded is the empty-state prototype (ships with 3 demo students / 2 demo teachers / 2 demo books seeded on first run, `finishInit(restored=false)`). If you have a browser's actual `localStorage` export with real entered marks, upload that JSON and I will write the import script against real data instead of guessing.

## 16. Public website pages, sections, navigation, content

Single-page-app style navigation (`data-page` attributes, JS show/hide, no real routing/URLs) with these pages:
**Home · About · Academics · Admissions · Gallery · News & Events · Contact**, plus an **"ERP Login"** button that opens the credential gate. Footer repeats the same nav links. I have not transcribed the full marketing copy here since it's lengthy and not needed for architecture planning — I can extract it verbatim into a content/copy doc in Phase 1 if useful for the Next.js migration.

## 17. Other important business rules hidden in the JS

- **The "Main Exam" test slot and the "Main Marksheet" are two different things** that are easy to conflate: "Main Exam" (`main` key) is just one of the six components you type marks into; "Main Marksheet" is the **combined view/report** across all six components. Naming this clearly in the data model will prevent confusion later.
- Roll numbers are **not validated for uniqueness** anywhere (data-integrity gap).
- Deleting a student is an **irreversible, un-audited cascading client-side delete**.
- The visual "maroon" CSS variable (`--maroon: #14213D`) is actually a **dark navy blue**, not maroon — the real accent pairing used throughout is **Navy (`--maroon`/`--maroon-dark`) + Gold (`--gold: #C9A227`)**, matching your "Navy/gold visual identity" requirement despite the confusing variable name. Fonts: **Fraunces** (display/serif headings), **IBM Plex Sans** (body), **IBM Plex Mono** (numeric/tabular data). A `data-theme="dark"` variant exists with its own CSS variable overrides.
- Excel export depends on a **third-party CDN script** (`cdnjs.cloudflare.com/.../xlsx.full.min.js`) loaded at runtime inside the base64-embedded iframe — a production app must vendor this or replace it with a backend-generated export for reliability and to avoid trusting a CDN at runtime.
- Auto-save runs every 2 seconds **unconditionally**, even with no changes — fine for a client-only demo, but not an appropriate pattern for a real API (would need debouncing / explicit save actions / autosave-with-diffing in production).

---

# PART 2 — COMPARISON: PROTOTYPE vs. PROPOSED PRODUCTION ARCHITECTURE

| | |
|---|---|
| **✅ Directly preserve (business logic / UX)** | Exact FST/SST/UT1/UT2/Internal(3-part)/Main formula and weightages (§5); exact grade boundaries (§6); exact pass/fail semantics including the compensatory subject-total rule (§7); exact ranking/tie logic (§8); report-card layout, letterhead, stamp, watermark, seal, signature block, A4-landscape print styling (§10); Navy+Gold+Fraunces/IBM-Plex visual identity; marks-entry workflow (per-test tabs, roster shared across tests, bulk-paste add-students); Internal Marks 3-part breakdown UX; public website page set/navigation/content. |
| **🔧 Needs normalization (schema-level)** | `subjects` (flat string array) → proper `Subject` entity with IDs, reusable across classes/years. `classLabel`/`year` (free strings) → real `Class`, `Section`, `AcademicYear` entities. `guardian`/`guardianPhone` (flat strings) → `Guardian` entity + `StudentGuardian` join (supports multiple guardians, phone/email, primary-contact flag). The five hardcoded `TESTS` + virtual Internal component → data-driven `Exam` + `ExamComponent` rows (so exam types are configurable per academic year without a code change). `feeTotals`/`feePayments` (flat) → proper `FeeStructure`/`FeeInvoice`/`FeePayment` model. `books`/`issues` (no ISBN/copy IDs/due dates) → `Book`/`BookCopy`/`BookIssue` with due dates and fines. Binary attendance `P`/`A` → status enum supporting Late/Half-day/Excused, plus a proper aggregation layer for term/year attendance % (doesn't exist in the prototype at all). |
| **🔒 Needs redesign for security** | The entire authentication system: hardcoded plaintext client-side credentials with **zero** backend validation and **zero** role differentiation must be fully replaced with server-side auth, HttpOnly cookies, and a real Role/Permission system (§3 below) — there is nothing to "migrate" here, it must be built new, guided by your Role-Permission Matrix requirements. Roll-number uniqueness must be enforced server-side (DB constraint). Hard deletes need soft-delete + audit logging (§ Audit Logs, non-existent in prototype). Marks-entry and report generation need role-gated write access (currently any logged-in user can edit/delete anything). |
| **📦 Needs migration (data)** | If real (non-demo) prototype data exists in a browser's `localStorage["khs_erp_data_v1"]`, its JSON shape is fully documented in §15 above and can be scripted into an idempotent import against the new schema (students → normalized Student+Guardian rows; marks → normalized Marks rows per ExamComponent; attendance/fees/library likewise). **Please export and upload that JSON if it exists** — otherwise Phase 0 will only need to seed demo/test data, not migrate anything real. |
| **❓ Information missing (not in prototype, needs your decision)** | Whether one login should manage multiple classes/sections simultaneously (assumed **yes** for production, per your ERD ask — prototype only ever supports one). Whether per-subject max/pass marks should vary (prototype applies one max/pass per test across all subjects uniformly). Whether grace marks / supplementary exams / attendance-linked eligibility should exist (none exist today). What "Publish" should mean per module for your permission matrix (prototype has no concept of draft vs. published anything — I'll propose sensible defaults in §3, please review). Real user roles' exact scope (e.g., can a Teacher only edit their own assigned subject's marks, or any subject in their class?) — I'll propose defaults, please confirm/adjust. |
| **⚠️ Contradictions / risks in the requested schema to flag** | Your ERD list includes `Users` and `Students`/`Teachers` as separate items — recommend explicitly modeling `User` as the auth/login table and `Student`/`Teacher`/`Parent`/`Staff` as **profile tables with a 1:0..1 link to User**, since not every Student record necessarily needs a login (younger students, or a transition period before all Parent accounts are onboarded) — this needs your confirmation as an assumption baked into the ERD below. The "Main Exam" vs. "Main Marksheet" naming ambiguity (§17) should be resolved with clear naming in the schema (e.g. `Exam.code = 'MAIN'` vs. a computed/materialized `ReportCard` per student per exam-group) to avoid confusion for future developers. |

---

# PART 3 — FINAL ARCHITECTURE

## 3.1 Final Technology Stack

| Layer | Choice | Notes |
|---|---|---|
| **Frontend** | **Next.js 14+ (App Router), TypeScript, React** | Two separate Next.js apps: `public-site` and `erp`, sharing a `packages/ui` design-system package (Navy/Gold/Fraunces/IBM-Plex tokens extracted from the prototype's CSS variables). |
| **Backend** | **Django 5 + Django REST Framework** | Chosen per your direction — CRUD-heavy domain, benefits from Django admin (useful for Admin/Principal power-user workflows and initial data fixes), built-in migrations, mature auth/permission primitives (`django.contrib.auth` + DRF permission classes) as the foundation for the Role-Permission Matrix. |
| **Database** | **PostgreSQL 16** | Managed via Docker Compose locally; one primary schema. `django-environ` for config. All numeric mark fields stored as `DecimalField` (never float) to avoid rounding errors in percentage/grade math. |
| **File storage** | **S3-compatible object storage** (MinIO locally in Docker; AWS S3 or equivalent in production) via `django-storages` | Used for report-card PDFs, uploaded documents, student photos. Never store files on the app server's local disk. |
| **Authentication** | **Server-side session auth via HttpOnly, Secure, SameSite cookies** (Django's session framework, not raw JWT-in-localStorage) | Login endpoint sets the cookie; DRF `SessionAuthentication` + CSRF token exchange for the ERP's cross-subdomain calls. Role/permission enforced with a custom `Role` + `Permission` model (or Django Groups if simpler — decided in Phase 0) checked on **every** write endpoint server-side, never trusting the frontend. |
| **API** | **REST, versioned under `/api/v1/`** | DRF ViewSets + routers per app; OpenAPI schema auto-generated (`drf-spectacular`) and committed to `docs/` for frontend type generation. |
| **Deployment** | **Docker + GitHub (Actions for CI, Container Registry for images)** | `docker-compose.yml` for local dev (postgres, minio, backend, erp-frontend, public-frontend, nginx). Production: same images behind a reverse proxy routing `kathwadahighschool.edu.in` → public-site and `erp.kathwadahighschool.edu.in` → erp app, both calling the same backend API. |

## 3.2 Final Database ERD

```mermaid
erDiagram
    USER ||--o| STUDENT : "1:0..1 login"
    USER ||--o| TEACHER : "1:0..1 login"
    USER ||--o| GUARDIAN : "1:0..1 login"
    USER ||--o| STAFF_PROFILE : "1:0..1 login"
    USER }o--|| ROLE : "has"

    ACADEMIC_YEAR ||--o{ CLASS_SECTION : "offered in"
    CLASS ||--o{ CLASS_SECTION : "has sections"
    CLASS_SECTION ||--o{ ENROLLMENT : "contains"
    STUDENT ||--o{ ENROLLMENT : "enrolled via"
    CLASS_SECTION }o--o{ SUBJECT : "offers (via CLASS_SECTION_SUBJECT)"
    TEACHER }o--o{ CLASS_SECTION_SUBJECT : "assigned to (via TEACHER_ASSIGNMENT)"

    STUDENT ||--o{ STUDENT_GUARDIAN : "has"
    GUARDIAN ||--o{ STUDENT_GUARDIAN : "guardian of"

    ACADEMIC_YEAR ||--o{ EXAM : "scheduled in"
    EXAM ||--o{ EXAM_COMPONENT : "made of"
    EXAM_COMPONENT ||--o{ EXAM_COMPONENT_SUBJECT_CONFIG : "max/pass per subject"
    SUBJECT ||--o{ EXAM_COMPONENT_SUBJECT_CONFIG : "configured for"

    STUDENT ||--o{ MARK : "scores"
    EXAM_COMPONENT ||--o{ MARK : "recorded for"
    SUBJECT ||--o{ MARK : "in subject"
    MARK }o--|| USER : "entered_by"

    STUDENT ||--o{ REPORT_CARD : "has"
    EXAM ||--o{ REPORT_CARD : "generated for"
    REPORT_CARD ||--o{ REPORT_CARD_SUBJECT_RESULT : "breakdown"
    REPORT_CARD ||--o| DOCUMENT : "pdf export"

    STUDENT ||--o{ ATTENDANCE_RECORD : "has"
    CLASS_SECTION ||--o{ ATTENDANCE_RECORD : "context"
    USER ||--o{ ATTENDANCE_RECORD : "marked_by"

    CLASS_SECTION ||--o{ FEE_STRUCTURE : "defines"
    STUDENT ||--o{ FEE_INVOICE : "billed"
    FEE_STRUCTURE ||--o{ FEE_INVOICE : "generates"
    FEE_INVOICE ||--o{ FEE_PAYMENT : "paid via"

    BOOK ||--o{ BOOK_COPY : "has copies"
    BOOK_COPY ||--o{ BOOK_ISSUE : "issued as"
    STUDENT ||--o{ BOOK_ISSUE : "borrows"

    STUDENT ||--o{ DOCUMENT : "owns"
    TEACHER ||--o{ DOCUMENT : "owns"

    USER ||--o{ AUDIT_LOG : "acted as"
```

### Key entities & fields (summary — full column list will be finalized as Django models in Phase 0)

- **User** — `id, email (unique), password_hash, role_id, is_active, last_login_at, mfa_enabled`. This is the auth table only.
- **Role** — `id, name (Admin/Principal/Teacher/Staff/Student/Parent), description`. Permissions attached via a `Permission`/`RolePermission` model or Django Groups — decided during Phase 0 implementation, doesn't change the ERD shape.
- **Student** — `id, user_id (nullable), admission_no (unique), first_name, last_name, dob, address, photo_document_id, created_at, updated_at`.
- **Guardian** — `id, user_id (nullable), name, phone, email, relationship`.
- **StudentGuardian** (join) — `student_id, guardian_id, is_primary_contact`.
- **Teacher** — `id, user_id, first_name, last_name, phone, email, joined_date`.
- **AcademicYear** — `id, label (e.g. "2025–26"), start_date, end_date, is_current`.
- **Class** — `id, name (e.g. "Std 10")`.
- **Section** — `id, class_id, name (e.g. "A")` — modeled as its own table so a Section can theoretically be reused across classes if the school ever wants that; `ClassSection` below is the actual per-year offering.
- **ClassSection** — `id, class_id, section_id, academic_year_id, class_teacher_id (nullable FK→Teacher)`.
- **Subject** — `id, name, code`. Reusable across classes/years (fixes the prototype's biggest gap).
- **ClassSectionSubject** (join) — `class_section_id, subject_id`.
- **TeacherAssignment** — `teacher_id, class_section_subject_id`.
- **Enrollment** — `student_id, class_section_id, roll_no (unique per class_section), status (active/transferred/graduated)`. **`roll_no` uniqueness enforced by a DB constraint scoped to `class_section_id`** — fixes the prototype's data-integrity gap (§17).
- **Exam** — `id, academic_year_id, code (e.g. FST/SST/UT1/UT2/MAIN/INTERNAL), name, sequence_order`. Data-driven replacement for the hardcoded `TESTS` array.
- **ExamComponent** — `id, exam_id, name (e.g. "Part 1", or the exam itself for simple exams), sequence_order`. Models the Internal exam's 3 sub-parts generically; a simple exam like FST has exactly one component.
- **ExamComponentSubjectConfig** — `exam_component_id, subject_id, class_section_id, max_marks, passing_marks`. Allows per-subject max/pass overrides (an improvement over the prototype's uniform-per-test values), while a default can still be applied uniformly to match current behavior.
- **Mark** — `id, student_id, exam_component_id, subject_id, marks_obtained (decimal), entered_by_id, entered_at, updated_at`. Unique constraint on `(student_id, exam_component_id, subject_id)`.
- **ReportCard** — `id, student_id, exam_id (the "Main" exam group), overall_total, overall_max, overall_pct, overall_grade, rank, result, generated_at, generated_by_id, pdf_document_id`. A cached/materialized rollup (recomputed on demand or on a signal after Mark changes) — mirrors `computeMain()` exactly, just persisted server-side instead of recomputed in the browser every render.
- **ReportCardSubjectResult** — `report_card_id, subject_id, component_breakdown (jsonb, e.g. {fst:.., sst:.., internal:..}), subject_total, subject_pct, subject_grade, subject_pass (bool)`.
- **AttendanceRecord** — `id, student_id, class_section_id, date, status (present/absent/late/excused), marked_by_id, marked_at`. Unique on `(student_id, date)`.
- **FeeStructure** — `id, class_section_id, academic_year_id, fee_head (e.g. Tuition/Transport), amount, due_date`.
- **FeeInvoice** — `id, student_id, fee_structure_id, amount_due, status`.
- **FeePayment** — `id, fee_invoice_id, amount, paid_at, method, recorded_by_id`.
- **Book** — `id, title, author, isbn, category`.
- **BookCopy** — `id, book_id, barcode, status (available/issued/lost)`.
- **BookIssue** — `id, book_copy_id, student_id, issued_at, due_at, returned_at, fine_amount`.
- **Document** — `id, owner_type (polymorphic: student/teacher/reportcard), owner_id, document_type, s3_key, uploaded_by_id, uploaded_at`.
- **AuditLog** — `id, actor_user_id, action (create/update/delete/publish/export), entity_type, entity_id, before_json, after_json, ip_address, created_at`. Does not exist in the prototype at all — new for production, populated via Django signals or DRF viewset hooks on every mutating request.

## 3.3 Role-Permission Matrix

Legend: **V**=View **C**=Create **E**=Edit **D**=Delete **P**=Publish **X**=Export · `—` = no access

This is a **proposed default**, since the prototype has no role concept to migrate from (§14). Please review and adjust before Phase 0.

| Module | Admin | Principal | Teacher | Staff | Student | Parent |
|---|---|---|---|---|---|---|
| Students | VCEDX | VCEX | V (own class only) | VCEX | V (own record) | V (own children) |
| Guardians | VCEDX | VEX | V | VCEX | — | V (own record), E (own contact info) |
| Teachers | VCEDX | VEX | V (own record), E (own contact info) | V | — | — |
| Classes / Sections | VCEDX | VCEX | V (assigned only) | VX | V (own class) | V (own child's class) |
| Subjects | VCEDX | VEX | V | V | V | V |
| Academic Years | VCEDX | VX | V | V | V | V |
| Exams & Exam Components | VCEDX | VCEX | V | V | V (own results) | V (own child's results) |
| Marks Entry | VCEDX | VEX (override/moderation) | VCE (assigned subjects/classes only) | — | V (own, once published) | V (own child's, once published) |
| Attendance | VCEDX | VEX | VCE (own classes only) | VC | V (own) | V (own child's) |
| Fees | VCEDX | VX | — | VCEX | V (own) | V (own child's), X (own receipts) |
| Library | VCEDX | VX | V, C (issue/return) | VCEDX | V (own issues) | V (own child's issues) |
| Documents | VCEDX | VX | VC (own uploads) | VC | V (own) | V (own child's) |
| Report Cards | VCEDPX | VEPX (approve/publish) | VC (draft, assigned classes) | VX | V (own, once published) | V (own child's, once published), X |
| Audit Logs | VX | VX | — | — | — | — |
| Users & Role Management | VCEDX | — | — | — | — | — |
| Public Website Content (CMS) | VCEDPX | VEP | — | — | — | — |

Notes on the design intent:
- **Teachers** are scoped to only the classes/subjects they're assigned to (`TeacherAssignment`) — enforced server-side via DRF permission classes, never trusted from the frontend.
- **Marks/Report Cards use a draft → publish workflow**: Teachers can enter/edit marks and generate a draft report card; only Principal/Admin can "Publish," at which point Students/Parents gain View access. This directly maps to the `Publish` column you asked for and prevents students seeing unfinalized marks.
- **Students/Parents never get Create/Edit/Delete on academic data** — their only writes anywhere are Guardian contact-info self-service edits.
- **Staff** (non-teaching, e.g. front-office) get Fees/Library/Attendance-marking access but not academic record editing.

## 3.4 Monorepo / Project Structure

```text
kathwada-school/
├── frontend/
│   ├── apps/
│   │   ├── public-site/        # Next.js — marketing website (Home/About/Academics/Admissions/Gallery/News/Contact)
│   │   └── erp/                 # Next.js — the ERP (erp.kathwadahighschool.edu.in)
│   └── packages/
│       ├── ui/                  # Shared design system: Navy/Gold tokens, Fraunces/IBM-Plex, buttons, tables, report-card print layout
│       └── api-client/          # Generated TypeScript client from the backend's OpenAPI schema
├── backend/
│   ├── config/                  # Django project settings (base/dev/prod split), root urls.py, wsgi/asgi
│   └── apps/
│       ├── accounts/             # User, Role, Permission, auth endpoints, cookie session views
│       ├── academics/            # AcademicYear, Class, Section, ClassSection, Subject, Enrollment
│       ├── people/               # Student, Teacher, Guardian, StudentGuardian, TeacherAssignment, Staff
│       ├── exams/                 # Exam, ExamComponent, ExamComponentSubjectConfig
│       ├── marks/                 # Mark, grading/ranking/pass-fail computation logic (ported 1:1 from §5–§9)
│       ├── reportcards/          # ReportCard, ReportCardSubjectResult, PDF generation, publish workflow
│       ├── attendance/            # AttendanceRecord + aggregation/reporting endpoints
│       ├── fees/                  # FeeStructure, FeeInvoice, FeePayment
│       ├── library/               # Book, BookCopy, BookIssue
│       ├── documents/             # Document model, S3 upload/download endpoints
│       ├── audit/                 # AuditLog model + DRF middleware/signal hooks
│       └── common/                # Shared base models (TimeStamped, SoftDelete), permission base classes, pagination
├── shared/
│   ├── openapi/                  # Committed OpenAPI schema (source of truth for frontend type generation)
│   └── design-tokens/            # Raw design tokens (colors/fonts/spacing) consumed by frontend/packages/ui
├── docs/
│   ├── architecture.md            # This document, kept up to date
│   ├── decisions/                 # ADRs (architecture decision records) for future major choices
│   └── migration/                 # Legacy prototype data-shape notes + import script docs
├── docker/
│   ├── docker-compose.yml
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── nginx/                     # Reverse-proxy config routing the two subdomains to the two Next.js apps + shared API
├── scripts/
│   └── import_legacy_localstorage.py   # One-off migration script (see §15/Migration Strategy)
├── .github/
│   └── workflows/                 # CI: backend tests, frontend build/lint, Docker image build
└── README.md
```

**What belongs where, briefly:**
- `frontend/apps/*` — deployable Next.js apps only; no shared business logic lives here beyond page composition.
- `frontend/packages/ui` — the actual "shared design system/branding" your brief requires the two frontends to share; both apps import from it so a rebrand only happens in one place.
- `backend/apps/*` — one Django app per bounded domain, matching the ERD sections above 1:1, so it's obvious where new logic goes.
- `shared/openapi` — makes the REST contract a first-class, version-controlled artifact instead of something the two frontends have to infer.
- `scripts/` — anything one-off (data migration, backfills) lives outside the Django app code so it's clearly not part of the running application.

## 3.5 Phase 0 Implementation Checklist

Each task should be independently verifiable. **Do not start Phase 1 until every box below is checked and demonstrated.**

- [ ] **0.1 — Repo scaffold.** Monorepo initialized with the folder structure above; root `README.md` explains how to run everything locally; linting/formatting configured for both Python (ruff/black) and TypeScript (eslint/prettier); `.env.example` files for backend and both frontends. *Done when:* a fresh clone + documented setup steps produce a working dev environment with no manual guesswork.
- [ ] **0.2 — Docker Compose skeleton.** `docker-compose.yml` brings up Postgres, MinIO (S3-compatible), the Django backend, and both Next.js apps. *Done when:* `docker compose up` succeeds from a clean checkout and all containers report healthy.
- [ ] **0.3 — Django project bootstrap.** `backend/config` created with dev/prod settings split; DRF installed; a `/api/v1/health/` endpoint returns `200 {"status":"ok"}`. *Done when:* a test hits that endpoint and passes in CI.
- [ ] **0.4 — PostgreSQL wired.** Django connects to Postgres via env vars; `python manage.py migrate` runs cleanly against a fresh database (even with just Django's built-in tables at this point). *Done when:* migrations run twice in a row with no errors (idempotency check).
- [ ] **0.5 — Custom User model.** Email-based `User` model (not Django's default username-based one) created **before any other migrations depend on it** (this must happen first or it's very costly to change later). *Done when:* `python manage.py createsuperuser` works against the custom model and the Django admin loads.
- [ ] **0.6 — Session-cookie auth end-to-end.** Login endpoint (`POST /api/v1/auth/login/`) sets an HttpOnly session cookie; logout endpoint clears it; a `GET /api/v1/auth/me/` endpoint returns the current user or 401. *Done when:* an automated test logs in, calls `/me/`, logs out, and confirms `/me/` then returns 401 — with **no password ever exposed in a response body**.
- [ ] **0.7 — CORS/CSRF for cross-subdomain cookies.** Configured so `erp.kathwadahighschool.edu.in` (frontend) can call the API with credentials, and CSRF tokens are correctly issued/validated for unsafe methods. *Done when:* a real cross-origin request (not `localhost`-to-`localhost`) in a local multi-subdomain Docker setup succeeds with cookies attached and fails without them.
- [ ] **0.8 — Role/Permission scaffold.** `Role` model (or Django Groups, decided during this task) created with the six roles from §3.3; a base DRF permission class that reads the role and denies by default. *Done when:* a test user with role=Student gets `403` on a stub admin-only endpoint, and role=Admin gets `200` on the same endpoint.
- [ ] **0.9 — ERP frontend shell.** Next.js `erp` app with a real login page calling the real backend (§0.6), and a protected empty dashboard page that redirects unauthenticated users to login. *Done when:* logging in with a seeded test user reaches the dashboard; an incognito/unauthenticated visit is redirected.
- [ ] **0.10 — Public site shell.** Next.js `public-site` app with at least the Home page ported over, using the shared `packages/ui` design tokens (Navy/Gold/Fraunces/IBM Plex) extracted from the prototype's CSS variables. *Done when:* a visual side-by-side with the prototype's Home page confirms the identity matches (colors, fonts, spacing).
- [ ] **0.11 — S3-compatible storage wired.** MinIO running via Docker Compose locally; `django-storages` configured; one test endpoint that uploads a small file and returns a working download URL. *Done when:* a round-trip upload/download test passes in CI.
- [ ] **0.12 — CI pipeline.** GitHub Actions workflow runs backend tests (pytest/Django test runner) and frontend build+lint on every PR; fails the PR on any red check. *Done when:* a deliberately broken test/lint rule fails the PR check, and fixing it turns the check green.
- [ ] **0.13 — Legacy data shape documented & dry-run parser.** A script (`scripts/import_legacy_localstorage.py`) that accepts the `khs_erp_data_v1` JSON shape (§15) and **parses/validates it into the new normalized structures in memory, printing a summary report** — **no database writes yet**. *Done when:* run against the prototype's demo-seeded JSON (or your real exported data, if you provide it), the script prints correct counts (e.g. "3 students, 6 subjects, 0 marks entered") with zero errors.
- [ ] **0.14 — Deployment smoke test.** All Docker images build successfully in CI (not just run locally); a documented one-command way to bring up the full stack. *Done when:* a teammate unfamiliar with the project can follow `README.md` alone and get a working local environment.

---

## Open questions before I begin implementation

1. Do you have an actual browser export of `localStorage["khs_erp_data_v1"]` with real (non-demo) student data, or should Phase 0's migration script only be validated against the prototype's demo-seeded data?
2. Please confirm the compensatory (aggregate subject-total) pass/fail rule in §5/§7 is intentional and should be preserved exactly, since it's a subtle rule that's easy to accidentally "fix" into something stricter.
3. Please review and adjust the Role-Permission Matrix (§3.3) and the draft→publish workflow assumption for marks/report cards — the prototype gave no guidance here, so this is my proposal, not a migration.
4. Should production support multiple simultaneous class-sections under one login (assumed yes), confirming the ERD's `ClassSection`/`Enrollment` design is the right shape?

Once you confirm/adjust the above, I'll proceed to Phase 0 exactly per the checklist in §3.5 — nothing further will be implemented until you give the go-ahead.
