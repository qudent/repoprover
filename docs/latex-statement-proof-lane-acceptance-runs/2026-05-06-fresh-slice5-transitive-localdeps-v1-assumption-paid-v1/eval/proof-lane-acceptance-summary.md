# Proof-Lane Acceptance Summary

- Base generation run: `docs/latex-statement-panel-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1/generation`
- Proof-lane task dir: `docs/latex-statement-proof-lane-tasks/2026-05-06-fresh-slice5-transitive-localdeps-v1-assumption`
- Output run: `docs/latex-statement-proof-lane-acceptance-runs/2026-05-06-fresh-slice5-transitive-localdeps-v1-assumption-paid-v1`
- Solution units: `unit-001, unit-002, unit-003, unit-004, unit-005`
- Verification compile: `0/5`
- Verification failure classes: `{'compile_failure': 2, 'declined_cannot_prove': 3}`
- Semantic coverage: `0/5` all aligned gold proved
- Semantic status counts: `{'generated_not_compiled': 5}`

## Solution Unit Results

| Unit | Compile | Failure class | Semantic status |
|---|---:|---|---|
| unit-001 | False | `declined_cannot_prove` | `generated_not_compiled` |
| unit-002 | False | `compile_failure` | `generated_not_compiled` |
| unit-003 | False | `declined_cannot_prove` | `generated_not_compiled` |
| unit-004 | False | `compile_failure` | `generated_not_compiled` |
| unit-005 | False | `declined_cannot_prove` | `generated_not_compiled` |

Caveat: semantic/exact gold checks are post-hoc grader-only checks. They are not proof-lane prompt context.
