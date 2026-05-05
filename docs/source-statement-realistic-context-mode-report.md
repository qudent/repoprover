# Source-Statement Realistic Context Mode

Date: 2026-05-05

## Motivation

The 6/6 strict hard-slice result is useful, but it was not a fully realistic
book-autoformalization setting. Several prompt improvements used source-facing
Lean target doc comments, target-derived alignment labels, or hidden target
declaration names as internal guidance triggers. Those surfaces are good for
debugging, but they can overfit to the existing formalization.

This checkpoint adds an explicit prompt context mode:

- `target-comment`: the previous mode. It withholds the target Lean statement
  and name from the model, but still uses target Lean doc comments and
  target-derived alignment labels as source-facing focus metadata. It also keeps
  imported same-source-label API retrieval.
- `source-only`: the stricter mode. It removes target Lean doc comments,
  target-derived comment labels, hidden target-name guidance triggers, and
  imported source-label API retrieval. The prompt is driven by the TeX/source
  span, file/prefix context, prior same-file local APIs, local style examples,
  and generic domain guidance.

The new mode is selected with:

```bash
--context-mode source-only
```

## Zero-Cost Artifacts

Two source-only budget-only checkpoints were generated.

Strict six-row hard slice:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records docs/source-statement-runs/2026-05-05-strict-guidance-six-generation/eval/selected-records.jsonl \
  --output docs/source-statement-runs/2026-05-05-strict-guidance-six-source-only-budget \
  --limit 6 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --budget-only \
  --context-mode source-only --max-tokens 32768 --reasoning-effort high
```

Result:

- paid calls: `0`
- actual cost: `$0.00`
- estimated max generation cost: `$0.17953842`

Broader 11-record preflight-passing slice:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records docs/source-statement-runs/2026-05-05-preflight-passing-11-generation/eval/selected-records.jsonl \
  --output docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-budget \
  --limit 11 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --budget-only \
  --context-mode source-only --max-tokens 32768 --reasoning-effort high
```

Result:

- paid calls: `0`
- actual cost: `$0.00`
- estimated max generation cost: `$0.329193645`

Hidden-name check over the 11-record source-only prompt artifacts:

- absent `isSummable_of_coeffStabilizesTo_partial_sum`
- absent `fps_newtonBinomial_neg`
- absent `fps_comp_coeff_finite`
- absent `parts_eq_zero_of_partition_zero`
- absent `perm_pow_succ`
- absent `simpleTransposition_isSwap`
- absent `det_lowerTriangular`
- absent `coeffFinitelyDeterminedInProd_of_finite`
- absent `exists_xn_approximator`
- absent `binom_symm`
- absent `X_mul_eq_shift`

The row 1 source-only payload also has
`prefix_has_imported_label=false`, confirming that imported source-label API
retrieval is disabled in this mode.

## Context Gap Audit

The comparison tool:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/compare_source_statement_context_modes.py \
  --target-comment-run docs/source-statement-runs/2026-05-05-preflight-passing-11-generation \
  --source-only-run docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-budget \
  --output-json docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-budget/eval/context-mode-comparison.json \
  --output-md docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-budget/eval/context-mode-comparison.md
```

11-record result:

- rows with hidden target names in source-only payloads: `0`
- rows with target-comment terms absent from the source span: `7/11`
- source-only estimated max cost: `$0.329193645`

The same comparison over the strict six-row slice found `0` hidden target-name
hits and `5/6` rows where target-comment terms are absent from the source span.
That is the concrete context-selection gap: source-only prompts are cleaner, but
they often do not know which part of the TeX/source span the target formalizes.

## What Changed In The Prompt

In `source-only` mode:

- `target_source_focus.target_declaration_source_comment` is `null`;
- `target_source_focus.record_comment_labels` is empty;
- `specific_source_labels` and `specific_labeled_parts` are not inferred from
  target-derived comments;
- hidden target declaration names are not used for domain-guidance triggers;
- imported declarations found only by matching source labels are not injected.

This intentionally makes some prompts less helpful. For example, the
`fps_comp_coeff_finite` source-only prompt sees the source span label
`def.fps.subs`, but not the target doc-comment phrase “alternative coefficient
formula”. As a result, it does not receive the finite-coefficient
`finsum_eq_sum_of_support_subset` hint that the target-comment prompt received.
That is the point of this mode: it exposes where realistic context selection
needs to infer focus from TeX/source segmentation rather than from the target
Lean artifact.

## Tests

Focused tests passed:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run pytest \
  tests/test_source_statement_live_eval.py \
  tests/test_source_statement_generation_artifacts.py
```

Result: `61 passed`.

## Next Step

Use `source-only` as the default for realistic validation. The next work should
not be another hand-tuned six-row repair loop. It should build a TeX-derived
focus selector that can recover useful subtask cues, such as “finite coefficient
formula” or “part (a) only”, without reading target Lean comments or names.
