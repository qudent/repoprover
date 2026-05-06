# Proof-Lane Acceptance Summary

- Base generation run: `docs/latex-statement-repair-loop-runs/2026-05-06-fresh-slice5-repair-v1-paid-v2-compact/round-01-repair`
- Proof-lane task dir: `docs/latex-statement-proof-lane-tasks/2026-05-06-fresh-slice5-finiteness-merged`
- Output run: `docs/latex-statement-proof-lane-acceptance-runs/2026-05-06-fresh-slice5-unit004-finiteness-smoke`
- Solution units: `unit-004`
- Verification compile: `1/5`
- Verification failure classes: `{'compiled': 1, 'declined_cannot_prove': 4}`
- Semantic coverage: `1/5` all aligned gold proved
- Semantic status counts: `{'all_aligned_gold_proved': 1, 'generated_not_compiled': 4}`

## Solution Unit Results

| Unit | Compile | Failure class | Semantic status |
|---|---:|---|---|
| unit-004 | False | `declined_cannot_prove` | `generated_not_compiled` |

Caveat: semantic/exact gold checks are post-hoc grader-only checks. They are not proof-lane prompt context.
