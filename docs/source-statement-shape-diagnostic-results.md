# Source-Statement Shape Diagnostic Results

Date: 2026-05-05

## Change

Added `scripts/diagnose_source_statement_shape.py`, a no-cost artifact consumer
for archived source-statement generations. It reads each record's saved
`openrouter-payload.json` and `model-output.json`, uses only visible prompt
context plus the generated Lean declaration, and writes row-level
`shape-diagnostic.json` artifacts plus aggregate `eval/shape-diagnostic-*`
reports.

The diagnostic is intentionally separate from Lean verification. It catches
statement/proof-shape risks that can pass generated-only Lean compilation but
still fail the hidden grader because the generated theorem is too weak,
different, or based on the wrong local API family.

## Heuristics Covered

- pointwise conclusion instead of sequence/function equality for
  `embedUnivInBiv` coefficient projection;
- wrong side or special-case shape for `f * X^k` coefficient-shift targets;
- constructed `Fin` object inequalities instead of local value inequalities for
  simple transposition fixed-point statements;
- topological infinite-product APIs instead of the local finite-approximator
  API;
- swapped `PowerSeries.subst` argument order;
- informational warning when substitution proofs use the avoided
  `fps_comp_coeff` helper instead of the local `HasSubst.X'`/`coeff_subst'`
  proof shape.

## Archived Run Diagnostics

Hard-guidance run:
`docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-hard-guidance`

- Records: 8
- Records with warnings: 4
- Warning codes:
  `{"fin_object_inequality_instead_of_value_inequality": 1, "pointwise_conclusion_instead_of_sequence_equality": 1, "substitution_proof_uses_avoided_finite_composition_helper": 1, "wrong_x_power_multiplication_side_or_shape": 1}`
- The warning rows match the hard-guidance report's remaining semantic-shape
  failures on multivariate coefficient projection, `X^k` multiplication side,
  and simple transposition assumptions, plus one proof-shape warning on
  substitution.

Previous domain-guidance larger run:
`docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-domain-guidance`

- Records: 8
- Records with warnings: 3
- Warning codes:
  `{"fin_object_inequality_instead_of_value_inequality": 1, "topological_infprod_api_instead_of_local_approximator": 1, "wrong_x_power_multiplication_side_or_shape": 1}`
- The comparison shows the hard-guidance prompt removed the old topological
  infinite-product shape error, but introduced or exposed the pointwise
  sequence-equality mismatch.

## Commands

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/diagnose_source_statement_shape.py \
  --run-output docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-hard-guidance

UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/diagnose_source_statement_shape.py \
  --run-output docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-domain-guidance
```

Focused tests:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run pytest \
  tests/test_source_statement_generation_artifacts.py \
  tests/test_source_statement_live_eval.py \
  tests/test_minimal_context_smoke_materializer.py
```

Result: `50 passed in 1.16s`.

## Interpretation

The diagnostic gives the next iteration a cheap gate before spending more on
generation or repair. It should be used to route failures into one of two
queues:

- compile-only failures: generated-only compiler-feedback repair remains the
  right cheap path;
- shape warnings or grader-only failures: run a visible-context statement-shape
  rewrite or strengthen the prompt/context retrieval before asking for another
  proof.

This is still a heuristic layer, not a correctness oracle. It deliberately does
not inspect the hidden gold Lean statement.

## Shape-Warning Repair Queue

The archived repair queue now accepts shape diagnostic warnings:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/repair_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-preflight-passing-8-generation-hard-guidance \
  --verification-results verification-results.json \
  --attempt 2 \
  --include-shape-warnings \
  --shape-warnings-only \
  --shape-diagnostic-results shape-diagnostic-results.json \
  --max-tokens 32768 \
  --reasoning-effort high \
  --max-actual-cost-usd 0.18 \
  --concurrency 2
```

Result:

- Targeted rows: 4 shape-warning rows (`#3`, `#4`, `#5`, `#7`)
- Paid calls: 4
- Actual cost: `$0.01844748`
- Repair generations: 4/4 parsed
- Lean verification of attempt 2: 3/4 repaired rows passed generated-only and
  hidden-grader checks (`#3`, `#5`, `#7`); row `#4` still failed generated-only
  Lean.

A follow-up compiler-feedback pass on row `#4` only cost `$0.004717314` but
still failed generated-only Lean, with a remaining scalar-vs-multiplication
goal mismatch around `finsum_eq_single`.

Best cumulative hard-guidance result after this diagnostic-driven repair path:
6/8 verified successes for an added `$0.023164794` beyond the hard-guidance
run, or `$0.099924662` total for hard-guidance generation plus all repair
attempts recorded here.
