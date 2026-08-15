# Grading Engine — Test Specification (for Phase 3)

**Status:** Specification only. No grading logic is implemented yet — this
document exists so Phase 3 has an unambiguous, exhaustive acceptance test
suite to implement against, derived directly from the prototype's actual
behavior (architecture doc §5–§9), not from a re-interpretation of it.

Every test case below should become an actual automated test (pytest) once
the `marks`/`reportcards` apps are built in Phase 3. Until then, this is the
contract those apps must satisfy.

---

## 0. Source of truth

All formulas here are transcribed directly from the decoded prototype
(`computeTest`, `computeInternal`, `computeMain`, `getGrade`,
`ranksFromValues` — see architecture doc §5–§9). Where this spec and the
architecture doc disagree, the architecture doc's §5–§9 wording is
authoritative and this spec should be corrected, not the other way round.

## 1. Grade boundaries (`getGrade`)

Pure function: percentage → grade label. Same function used for single-test,
Internal, and combined Main views.

| Test ID | Input pct | Expected grade |
|---|---|---|
| GRADE-01 | 100 | A1 |
| GRADE-02 | 90.0 | A1 |
| GRADE-03 | 89.999 | A2 |
| GRADE-04 | 80.0 | A2 |
| GRADE-05 | 79.999 | B1 |
| GRADE-06 | 70.0 | B1 |
| GRADE-07 | 69.999 | B2 |
| GRADE-08 | 60.0 | B2 |
| GRADE-09 | 59.999 | C1 |
| GRADE-10 | 50.0 | C1 |
| GRADE-11 | 49.999 | C2 |
| GRADE-12 | 40.0 | C2 |
| GRADE-13 | 39.999 | D |
| GRADE-14 | 33.0 | D |
| GRADE-15 | 32.999 | E |
| GRADE-16 | 0.0 | E |

Boundaries are inclusive on the lower bound of each band (`>=`), per the
prototype's `if(pct>=90) return "A1"` chain. GRADE-03/05/07/09/11/13/15 exist
specifically to catch an off-by-one/wrong-comparison-operator bug (e.g. `>`
instead of `>=`) at every single boundary.

## 2. Single-test computation (`computeTest` — FST/SST/UT1/UT2/Main individually)

Setup for all cases in this section: 3 subjects, each test max=25, pass=8
(the prototype's FST/SST defaults), unless stated otherwise.

| Test ID | Subject marks (S1, S2, S3) | Expected total | Expected pct | Expected result |
|---|---|---|---|---|
| TEST-01 | 20, 20, 20 | 60 | 80.0 | PASS (all subjects ≥ 8) |
| TEST-02 | 20, 20, 5 | 45 | 60.0 | **FAIL** (S3 < pass mark 8, even though total/pct alone would look like a pass at a naive glance — this is the key "one weak subject fails the whole test" behavior to verify) |
| TEST-03 | 8, 8, 8 | 24 | 32.0 | PASS (every subject exactly at the passing mark — boundary case) |
| TEST-04 | 7.999, 25, 25 | — | — | **FAIL** (one subject 0.001 below passing mark — boundary case just under) |
| TEST-05 | 0, 0, 0 | 0 | 0.0 | FAIL |
| TEST-06 | 25, 25, 25 | 75 | 100.0 | PASS |

**TEST-02 is the single most important case in this section** — it verifies
that single-test pass/fail is a **per-subject gate**, not a total-marks gate.
An implementation that only checks `total >= (pass × numSubjects)` will
incorrectly PASS this case (45 ≥ 24) when the correct answer is FAIL.

## 3. Internal Marks computation (`computeInternal`)

Setup: p1 max=5, p2 max=5, p3 max=10 (total 20), internalPass=7 (combined
threshold, not per-part).

| Test ID | Subject's (p1, p2, p3) | Expected subject total | Expected subject result |
|---|---|---|---|
| INT-01 | 5, 5, 10 | 20 | PASS |
| INT-02 | 0, 0, 7 | 7 | PASS (exactly at combined threshold, even though p1/p2 are both zero — verifies the threshold is combined, NOT per-part) |
| INT-03 | 0, 0, 6.999 | 6.999 | FAIL |
| INT-04 | 2, 2, 2 | 6 | FAIL (6 < 7) |
| INT-05 | 2.5, 2.5, 5 | 10 | PASS (verifies 0.5-step / half-mark inputs are handled) |

INT-02 is the critical case: it must NOT be implemented as "each part has its
own minimum" — there is no such rule in the prototype.

## 4. Main Marksheet — the compensatory aggregate formula (`computeMain`)

**This is the highest-priority section of this whole spec.** Per your
explicit Phase 0 decision: preserve this exactly, do not tighten it into a
per-component pass requirement.

Setup: FST(max25/pass8), SST(max25/pass8), UT1(max50/pass17),
UT2(max50/pass17), Main(max80/pass26), Internal(max20/pass7 combined).
→ `subjectMax = 250`, `subjectPassReq = 83`.

### 4a. Subject-level compensatory pass logic

| Test ID | FST/SST/UT1/UT2/Main/Internal marks for one subject | Subject total | Subject result | Why this case matters |
|---|---|---|---|---|
| MAIN-01 | 20/20/40/40/70/18 | 208 | PASS | Straightforward pass, all components individually strong |
| MAIN-02 | **0**/25/50/50/80/20 | 225 | **PASS** | FST scored ZERO (would fail FST individually per TEST-02's logic) but the subject still passes on the Main Marksheet because the aggregate total (225) clears subjectPassReq (83). **This is the case that would break if someone "fixes" the logic to require every component to individually pass.** |
| MAIN-03 | 5/5/10/10/20/5 | 55 | FAIL | Every component is weak; aggregate total (55) < 83 |
| MAIN-04 | 8/8/17/17/26/7 | 83 | PASS | Every component exactly at ITS OWN individual passing mark, aggregate exactly equals subjectPassReq (83) — boundary case |
| MAIN-05 | 8/8/17/17/25.999/7 | 82.999 | FAIL | One unit below MAIN-04's boundary |

### 4b. Overall (all-subjects) result

Setup: 2 subjects.

| Test ID | Subject A result | Subject B result | Overall total vs overallPassReq (166) | Expected overall result | Why |
|---|---|---|---|---|---|
| OVERALL-01 | PASS (208) | PASS (208) | 416 ≥ 166 | PASS | Both conditions satisfied |
| OVERALL-02 | PASS (208) | FAIL (55) | 263 ≥ 166 | **FAIL** | Overall total alone would look like a pass, but Subject B individually failed — verifies "every subject passes AND overall total clears threshold" is an AND, not an OR, and that a strong subject cannot compensate for a failed subject at the overall level (compensation only happens WITHIN a subject across its 6 components, never ACROSS subjects) |
| OVERALL-03 | PASS (83) | PASS (83) | 166 ≥ 166 | PASS | Exact boundary — both subjects at their individual minimum, overall total exactly at overallPassReq |

OVERALL-02 is the second most important case in this whole document — it
verifies the two-part AND condition is implemented correctly and that
compensation does not leak across subjects.

## 5. Ranking & tie handling (`ranksFromValues`)

Standard/competition ranking: ties share a rank; the next distinct rank skips
by the number of tied students (dense-skip, "1224" pattern, not "1223").

| Test ID | Percentages (in student order) | Expected ranks (same order) |
|---|---|---|
| RANK-01 | 90, 80, 70 | 1, 2, 3 |
| RANK-02 | 90, 90, 80 | 1, 1, 3 |
| RANK-03 | 90, 90, 90, 80 | 1, 1, 1, 4 |
| RANK-04 | 70, 90, 80 | 2, 1, 3 (verifies ranking is by value, independent of input order) |
| RANK-05 | 50, 50, 50, 50 | 1, 1, 1, 1 |
| RANK-06 | 90, 85, 85, 80, 80, 80, 70 | 1, 2, 2, 4, 4, 4, 7 |

Also verify: ranking is computed **independently three times** — once for
each single test's own percentage, once for Internal's own percentage, and
once for the combined Main Marksheet's `overallPct`. A student's FST rank and
their Main Marksheet rank are unrelated numbers computed from different
underlying percentages — a test should assert these can legitimately differ
for the same student in the same dataset.

| Test ID | Scenario | Assertion |
|---|---|---|
| RANK-07 | Student X has the highest FST % but a middling combined Main % (e.g., aced FST, weak elsewhere) | X's FST-test rank = 1, X's Main-Marksheet rank ≠ 1 |

## 6. Cross-cutting / edge cases

| Test ID | Scenario | Expected behavior |
|---|---|---|
| EDGE-01 | Single student, single subject | Rank = 1 regardless of score; grade/pass logic still applies normally |
| EDGE-02 | Zero students in a class-section | Computation returns an empty result set, does not error |
| EDGE-03 | A subject with a mark of exactly `0` vs. a subject with no mark recorded at all | Must be distinguished if production adds "not yet entered" as a distinct state (the prototype does NOT distinguish these — an unset mark and a zero mark behave identically, per `num()` treating blank as 0 — confirm in Phase 3 whether production should preserve this or improve on it; **flagging as an explicit product decision needed, not assuming either way**) |
| EDGE-04 | Decimal/half-mark inputs (e.g., `17.5`) throughout FST/SST/UT1/UT2/Main/Internal | All totals, percentages, and threshold comparisons must use exact decimal arithmetic (production should use `Decimal`, never `float`, to avoid the classic `0.1 + 0.2 != 0.3` class of bug that the prototype's plain-JS-number arithmetic is itself already quietly exposed to) |
| EDGE-05 | Per-subject max/pass override (a Phase-1-onward capability the prototype doesn't have — see architecture doc's `ExamComponentSubjectConfig`) | Confirm the formulas above still hold correctly when different subjects have different max/pass values for the same component, not just a uniform value across all subjects as in every case above |

## 7. What Phase 3 must deliver against this spec

- One automated test per row above (or a parametrized test covering the
  table), named so the test ID (e.g. `TEST-02`, `MAIN-02`, `RANK-06`) is
  traceable from the test name back to this document.
- 100% pass rate against this spec is the Phase 3 acceptance gate for the
  grading engine specifically — separate from and in addition to whatever
  other Phase 3 acceptance criteria apply to the marks/report-card module as
  a whole.
- Any case where a genuine product ambiguity is found while implementing
  (EDGE-03 above is a known one already) must be raised for a decision before
  writing the implementation, not resolved by guessing.
