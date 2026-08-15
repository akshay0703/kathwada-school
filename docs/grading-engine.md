# Grading Engine — Business Rules

**Status: NOT IMPLEMENTED.** This document records the approved business
rules only. No `marks`/`reportcards` model or computation code exists yet
(planned for Phase 3). The acceptance test suite for the eventual
implementation is [`grading-engine-test-spec.md`](grading-engine-test-spec.md)
(30 hand-verified test cases) — **that file is not duplicated here.**

**These rules are authoritative and preserved exactly from the prototype
unless you explicitly approve a change.** They were extracted directly from
the prototype's actual JavaScript (`computeTest`, `computeInternal`,
`computeMain`, `getGrade`, `ranksFromValues`) — see `prototype-analysis.md`
§5–§9 for the original line-by-line extraction if you need to re-verify
against the source.

## The six components

FST, SST, UT1, UT2, Main — each a single mark per subject, with its own
configurable max/pass. Internal — a sixth, virtual component made of three
sub-parts (P1/P2/P3), each with its own max, but **one combined** passing
threshold across all three parts (not per-part).

## Three separate computations exist

1. **Single-test result** (FST/SST/UT1/UT2/Main, evaluated independently):
   a student's result for *that test* is PASS only if **every subject**
   individually meets that test's passing mark. This is a **per-subject
   gate**, not a total-marks gate — one weak subject fails the whole test
   result even if the total/percentage looks fine.

2. **Internal Marks result**: per subject, `P1 + P2 + P3` compared against
   one combined passing threshold (default 7 out of a 20 max). Not evaluated
   per-part.

3. **Main Marksheet result — the authoritative combined result** (this is
   "FST + SST + UT1 + UT2 + Internal + Main"):
   ```
   subjectTotal    = fst + sst + ut1 + ut2 + main + (p1+p2+p3)
   subjectPassReq  = sum of each component's own passing mark
   subjectPass     = subjectTotal >= subjectPassReq          ← COMPENSATORY / AGGREGATE

   overallTotal    = sum of subjectTotal across all subjects
   overallPassReq  = subjectPassReq × number of subjects
   finalResult     = PASS only if (every subject's subjectPass is true)
                                    AND (overallTotal >= overallPassReq)
   ```

## The rule you must never silently "fix"

**A subject passes the Main Marksheet if its aggregate total across all six
components clears the aggregate passing threshold — even if one individual
component was very weak or zero.** Example: a subject with FST=0 but strong
SST/UT1/UT2/Main/Internal can still pass overall, because passing here is
about the *sum*, not about clearing every individual component's own bar.

This is deliberately compensatory. It is **not** a bug, and Phase 3 must
**not** reinterpret it as "every component must individually pass." Your
explicit Phase 0 decision was to preserve this exactly as documented. See
test cases `MAIN-02` and `OVERALL-02` in `grading-engine-test-spec.md` for
the two cases that would silently break if this rule were ever "tightened."

Note the asymmetry: compensation happens **within** a subject, across its six
components. It does **not** happen **across** subjects — a strong Subject A
can never cover for a failed Subject B at the overall level (`OVERALL-02`).

## Grade boundaries (`getGrade`)

Pure percentage → label function, same function used for single-test,
Internal, and the combined Main view. Grade is a display label only — it does
not affect pass/fail.

| Band | Range |
|---|---|
| A1 | ≥ 90 |
| A2 | ≥ 80, < 90 |
| B1 | ≥ 70, < 80 |
| B2 | ≥ 60, < 70 |
| C1 | ≥ 50, < 60 |
| C2 | ≥ 40, < 50 |
| D | ≥ 33, < 40 |
| E | < 33 |

Boundaries are inclusive on the lower bound (`>=`) at every threshold — see
`GRADE-01` through `GRADE-16` in the test spec, which exist specifically to
catch an off-by-one at each boundary.

## Ranking & ties

Standard/competition ranking: sort descending by percentage; tied students
share a rank; the next distinct rank skips by the number of students tied
above it (dense-skip — e.g. two students tied at rank 2 means the next
student is rank 4, not rank 3). No secondary tiebreaker exists (not by best
subject, not alphabetical, not by roll number) — ties share a rank, full
stop.

Ranking is computed **independently three times**: once per single test
(its own percentage), once for Internal (its own percentage), and once for
the combined Main Marksheet (`overallPct`). A student's FST rank and their
Main Marksheet rank are unrelated numbers — see test spec case `RANK-07`.

## Defaults (editable, not hardcoded thresholds)

| Component | Default max | Default pass |
|---|---|---|
| FST | 25 | 8 |
| SST | 25 | 8 |
| UT1 | 50 | 17 |
| UT2 | 50 | 17 |
| Internal (P1+P2+P3) | 5+5+10=20 | 7 (combined) |
| Main | 80 | 26 |
| **Subject total** | **250** | **83** |

In production these live in `ExamComponentSubjectConfig`
(`database-schema.md`) — per-subject overrides are possible, but a uniform
default reproduces the prototype's current behavior exactly.

## Known open question (not yet decided)

`EDGE-03` in the test spec: the prototype does not distinguish "a mark of
exactly 0" from "no mark entered yet" — both behave identically. Whether
production should preserve this or introduce a distinct "not yet entered"
state is an explicit open product decision, not something to resolve by
guessing during Phase 3 implementation.
