# LaTeX Statement Verification Failure Overview

Generated: `2026-05-06T17:23:07.679990+00:00`

## `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro`

- Verification: `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro/eval/verification-results-360s.json`
- Units: `5`; compiled: `0`
- Failure classes: `{"compile_failure": 1, "declined_cannot_prove": 4}`
- Reported statuses: `{"cannot_prove_from_visible_context": 4, "generated": 1}`
- Contract violations: `{}`
- Placeholder tokens: `{}`
- Support totals: `{"accepted_count": 29, "candidate_count": 57, "elapsed_seconds": 0.0, "lean_call_count": 0, "rejected_count": 26, "skipped_count": 2}`

Top Lean error signatures:
- `1` x Unknown identifier \`isUnit_of_ne_zero\`

Unit rows:
- `unit-001` declined_cannot_prove status=cannot_prove_from_visible_context errors=0 support=1/12 accepted
- `unit-002` compile_failure status=generated errors=1 support=3/8 accepted
- `unit-003` declined_cannot_prove status=cannot_prove_from_visible_context errors=0 support=7/14 accepted
- `unit-004` declined_cannot_prove status=cannot_prove_from_visible_context errors=0 support=9/10 accepted
- `unit-005` declined_cannot_prove status=cannot_prove_from_visible_context errors=0 support=9/13 accepted

## `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-kimi-k2-6`

- Verification: `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-kimi-k2-6/eval/verification-results-360s.json`
- Units: `5`; compiled: `0`
- Failure classes: `{"compile_failure": 2, "declined_cannot_prove": 3}`
- Reported statuses: `{"cannot_prove_from_visible_context": 3, "generated": 2}`
- Contract violations: `{}`
- Placeholder tokens: `{}`
- Support totals: `{"accepted_count": 29, "candidate_count": 57, "elapsed_seconds": 0.0, "lean_call_count": 0, "rejected_count": 26, "skipped_count": 2}`

Top Lean error signatures:
- `1` x Unknown identifier \`fps_invertible_iff_constantCoeff\`
- `1` x unsolved goals
- `1` x Tactic \`apply\` failed: could not unify the conclusion of \`@funext\`
- `1` x Invalid rewrite argument: Expected an equality or iff proof or definition name, but \`signProduct ?e

Unit rows:
- `unit-001` declined_cannot_prove status=cannot_prove_from_visible_context errors=0 support=1/12 accepted
- `unit-002` compile_failure status=generated errors=2 support=3/8 accepted
- `unit-003` declined_cannot_prove status=cannot_prove_from_visible_context errors=0 support=7/14 accepted
- `unit-004` compile_failure status=generated errors=2 support=9/10 accepted
- `unit-005` declined_cannot_prove status=cannot_prove_from_visible_context errors=0 support=9/13 accepted

## `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro-highreason-units002-004`

- Verification: `docs/latex-statement-ablation-runs/2026-05-06-model-matrix/paid/fresh-proof-lane-pro-highreason-units002-004/eval/verification-results-360s.json`
- Units: `2`; compiled: `1`
- Failure classes: `{"compile_failure": 1, "compiled": 1}`
- Reported statuses: `{"generated": 2}`
- Contract violations: `{}`
- Placeholder tokens: `{}`
- Support totals: `{"accepted_count": 12, "candidate_count": 18, "elapsed_seconds": 258.225, "lean_call_count": 22, "rejected_count": 5, "skipped_count": 1}`
- Lean calls/elapsed: `28` / `367.128s`

Top Lean error signatures:
- `2` x Function expected at
- `1` x unexpected token ','; expected '↦', '=>'
- `1` x Tactic \`rewrite\` failed: Did not find an occurrence of the pattern
- `1` x Unknown constant \`Fin.snoc_injective\`
- `1` x Application type mismatch: The argument
- `1` x (deterministic) timeout at \`whnf\`, maximum number of heartbeats (200000) has been reached

Unit rows:
- `unit-002` compiled status=generated errors=0 support=3/8 accepted
- `unit-004` compile_failure status=generated errors=7 support=9/10 accepted

