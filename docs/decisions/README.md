# Architecture Decision Records

One file per significant decision, numbered sequentially. Template:

```
# NNNN — Title

Date: YYYY-MM-DD
Status: Proposed / Accepted / Superseded by NNNN

## Context
What problem forced this decision?

## Decision
What we chose.

## Consequences
What this makes easier or harder later.
```

## Recorded so far

- [`0001-role-permission-data-model.md`](0001-role-permission-data-model.md)
  — permissions as data, not code
- [`0002-preserve-compensatory-grading-rule.md`](0002-preserve-compensatory-grading-rule.md)
  — the Main Marksheet's aggregate pass rule is intentional, not a bug
- [`0003-multi-class-section-and-academic-year.md`](0003-multi-class-section-and-academic-year.md)
  — multiple simultaneous class-sections, first-class Academic Year, no
  overwriting history on promotion
- [`0004-ci-gated-deploys-via-render-deploy-hooks.md`](0004-ci-gated-deploys-via-render-deploy-hooks.md)
  — how automatic, CI-gated deployment works and why no Render API key was needed

Next to write, once Phase 1 starts: an ADR for whichever approach is chosen
for the blank-vs-zero-mark open question (`project-status.md` open decisions).
