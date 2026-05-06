# Proof-Lane Acceptance Summary

- Base generation run: `docs/latex-statement-repair-loop-runs/2026-05-06-dev-panel5-v2-repair-v5-merged-panel`
- Proof-lane task dir: `docs/latex-statement-proof-lane-tasks/2026-05-06-dev-panel5-v2-merged-panel`
- Output run: `docs/latex-statement-proof-lane-acceptance-runs/2026-05-06-dev-panel5-v2-proof-lane-paid-v1`
- Solution units: `unit-001, unit-005`
- Verification compile: `2/5`
- Verification failure classes: `{'compile_failure': 1, 'compiled': 2, 'declined_cannot_prove': 2}`
- Semantic coverage: `2/5` all aligned gold proved
- Semantic status counts: `{'all_aligned_gold_proved': 2, 'generated_not_compiled': 3}`

## Solution Unit Results

| Unit | Compile | Failure class | Semantic status |
|---|---:|---|---|
| unit-001 | False | `declined_cannot_prove` | `generated_not_compiled` |
| unit-005 | False | `declined_cannot_prove` | `generated_not_compiled` |

Caveat: semantic/exact gold checks are post-hoc grader-only checks. They are not proof-lane prompt context.
