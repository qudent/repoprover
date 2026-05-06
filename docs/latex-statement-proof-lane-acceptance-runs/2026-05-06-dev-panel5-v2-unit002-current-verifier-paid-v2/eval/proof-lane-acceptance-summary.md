# Proof-Lane Acceptance Summary

- Base generation run: `docs/latex-statement-proof-lane-acceptance-runs/2026-05-06-dev-panel5-v2-proof-lane-paid-v1`
- Proof-lane task dir: `docs/latex-statement-proof-lane-tasks/2026-05-06-dev-panel5-v2-current-verifier`
- Output run: `docs/latex-statement-proof-lane-acceptance-runs/2026-05-06-dev-panel5-v2-unit002-current-verifier-paid-v2`
- Solution units: `unit-002`
- Verification compile: `3/5`
- Verification failure classes: `{'compiled': 3, 'declined_cannot_prove': 2}`
- Semantic coverage: `3/5` all aligned gold proved
- Semantic status counts: `{'all_aligned_gold_proved': 3, 'generated_not_compiled': 2}`

## Solution Unit Results

| Unit | Compile | Failure class | Semantic status |
|---|---:|---|---|
| unit-002 | True | `compiled` | `all_aligned_gold_proved` |

Caveat: semantic/exact gold checks are post-hoc grader-only checks. They are not proof-lane prompt context.
