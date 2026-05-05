# Source-Statement Strict Guidance Budget Check

Date: 2026-05-05

This records the no-call prompt check after the 0/6 targeted-guidance retry.
The change tightens guidance based on the actual verification failures without
exposing hidden target declaration names.

## Added Constraints

- FPS limits: if the source-facing target comment only asks that the family is
  summable, require a theorem concluding only `IsSummable f`; explicitly reject
  a `tsum'` equality, `And.intro`, or `∧`.
- FPS substitution finite coefficients: require ordinary Lean support-subset
  syntax with `apply finsum_eq_sum_of_support_subset` and `intro d hd`; reject
  prose-like binders such as `intro d in`.
- Partition zero: prefer the direct statement `p.parts = 0` from
  `partition_zero_parts p`; reject uniqueness-of-partition statements and later
  same-file wrappers unless they are visible in the prompt.
- Permutation powers: when the source focus is the group-power law, prefer
  `α ^ (n + 1) = α ^ n * α`; reject pointwise `Function.iterate` statements
  unless the source explicitly asks for them.
- Simple transpositions: require the `(simpleTransposition i).IsSwap` statement
  shape and constructor-style proof shape; reject invented helpers such as
  `Equiv.swap_isSwap`.

## Zero-Cost Validation

Command:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records /tmp/repoprover-targeted-guidance-six-failures.jsonl \
  --output docs/source-statement-runs/2026-05-05-strict-guidance-six-budget \
  --limit 6 --sample-mode corpus-spread --include-record-imports \
  --budget-only --max-tokens 32768 --reasoning-effort high
```

Result:

- records completed: `6`
- paid calls made: `0`
- actual cost: `$0.00`
- estimated max one-shot generation cost for these six rows: `$0.180551535`

Mechanical payload checks passed:

- row 1 includes `Do not include a tsum' equality` and
  `conclude only IsSummable f`;
- row 7 includes `intro d hd` and the warning against `intro d in`;
- row 9 includes `p.parts = 0` and the warning against unavailable later
  wrappers;
- row 10 includes `α ^ (n + 1) = α ^ n * α` and the warning against
  `Function.iterate`;
- row 11 includes `constructor-style proof shape` and the warning against
  `Equiv.swap_isSwap`;
- emitted payloads do not contain hidden target names
  `fps_newtonBinomial_neg`, `fps_comp_coeff_finite`,
  `parts_eq_zero_of_partition_zero`, `perm_pow_succ`, or
  `simpleTransposition_isSwap`.

Focused tests:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run pytest \
  tests/test_source_statement_live_eval.py \
  tests/test_source_statement_generation_artifacts.py \
  tests/test_minimal_context_smoke_materializer.py
```

Result: `60 passed`.

## Interpretation

This is still a prompt-shape checkpoint, not evidence of improved model
quality. It justifies at most one small capped paid retry on the same six rows.
If that retry does not improve, the next useful path is a statement-shape-first
generation stage or row-specific visible examples, not more broad prose
guidance.
