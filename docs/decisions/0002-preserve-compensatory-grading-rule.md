# 0002 — Preserve the compensatory aggregate Main Marksheet pass rule exactly

Date: Phase 0
Status: Accepted

## Context

The prototype's authoritative Main Marksheet result computes, per subject,
`subjectTotal >= subjectPassReq` where `subjectTotal` sums all six components
(FST+SST+UT1+UT2+Main+Internal) and `subjectPassReq` sums their individual
passing marks. This means a subject can pass even if one component was very
weak or zero, as long as the aggregate clears the aggregate threshold. This
reads, at first glance, like it might be an oversight worth "fixing" into a
stricter per-component pass requirement.

## Decision

It is not a bug. You explicitly reviewed this exact behavior
(`prototype-analysis.md` §5/§7) and approved preserving it exactly,
unchanged, including the asymmetry that compensation happens *within* a
subject across its six components but never *across* subjects at the overall
level.

## Consequences

- `grading-engine.md` documents this rule in prose; the corresponding test
  cases `MAIN-02` and `OVERALL-02` in `grading-engine-test-spec.md` exist
  specifically to catch a future implementation that "fixes" this into a
  stricter rule.
- Individual FST/SST/UT1/UT2/Main test-level results keep their own,
  different, non-compensatory rule (every subject must individually clear
  that test's passing mark) — the two rules coexist and must not be
  conflated during implementation.
- Any future change to this behavior requires explicit, new approval — it
  cannot be inferred from "this looks like a bug."
