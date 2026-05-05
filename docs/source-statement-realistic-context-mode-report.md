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
- estimated max generation cost: `$0.18052935`

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
- estimated max generation cost: `$0.330879705`

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
- source-only estimated max cost after TeX environment-balance expansion:
  `$0.332716275`

The same comparison over the strict six-row slice found `0` hidden target-name
hits and `5/6` rows where target-comment terms are absent from the source span.
That is the concrete context-selection gap: source-only prompts are cleaner, but
they often do not know which part of the TeX/source span the target formalizes.

## First Paid Source-Only Generation

The first paid realistic-context validation used the broader 11-record
preflight-passing slice:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records docs/source-statement-runs/2026-05-05-preflight-passing-11-generation/eval/selected-records.jsonl \
  --output docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-generation \
  --limit 11 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --generation-only \
  --context-mode source-only \
  --max-actual-cost-usd 0.40 --concurrency 3 \
  --max-tokens 32768 --reasoning-effort high
```

Result:

- records generated: `11/11`
- paid calls: `11`
- actual cost: `$0.081084638`
- model: `deepseek/deepseek-v4-pro`
- Lean verification: `1/11` passed after serial reusable-project checking

Verification command:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/verify_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-generation \
  --work-root /tmp/repoprover-source-only-11-verify \
  --lake-cache-from algebraic-combinatorics --include-record-imports \
  --workers 1 --lean-timeout 180 \
  --output-prefix verification-180
```

Verification result:

- pass: `1/11` (`X_mul_eq_shift`)
- generated Lean did not compile: `8/11`
- generated Lean compiled but did not prove the withheld gold statement: `2/11`

The two compile-clean semantic misses are context/focus failures:

- `det_triangular` proved a broader upper/lower triangular disjunction theorem,
  but the withheld target expects the lower-triangular hypothesis directly.
- `simpleTransposition_sq_eq_one` proved an order-two theorem, but the withheld
  target expects `(simpleTransposition i).IsSwap`.

Several compile failures are ordinary Lean/API failures, for example wrong
PowerSeries integer-power syntax, unknown guessed helper names, reversed
binomial symmetry, and unsupported partition/permutation APIs. These are good
repair-prompt data, but not evidence that source-only context selection is
solved.

Visible-context shape diagnostics now report `0` warnings on this run after
tightening the diagnostic so it no longer treats broad prompt guidance as if it
were source evidence.

## First Source-Only Repair Pass

Compile-failure repair attempt 1 targeted only rows whose generated declaration
did not compile:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/repair_source_statement_generation.py \
  --run-output docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-generation \
  --verification-results verification-180-results.json \
  --generated-only-lean-name verification-180-generated-only-lean.json \
  --attempt 1 --max-tokens 32768 --reasoning-effort high \
  --max-actual-cost-usd 0.35 --concurrency 3
```

Generation result:

- targeted compile failures: `8`
- repair outputs generated: `7/8`
- paid calls: `7`
- actual cost: `$0.058516809`
- provider failure: row 1 failed with `openrouter_JSONDecodeError`

Verification result after adding targeted verifier indices:

- repairs verified: `7`
- repairs passing hidden-grader check: `3/7`
- still generated-only compile failures: `3/7`
- compiled but failed hidden-grader check: `1/7`

Passing repairs:

- `fps_onePlusX_pow_int`
- `exists_isXnApproximator_of_multipliable`
- `binom_sym`

Row 1 was retried in repair attempt 2 for `$0.013631334`, but the repair still
failed generated-only compilation (`coeff_sum` unknown and a range-membership
proof mismatch).

Cumulative realistic source-only result for this 11-row slice is now `4/11`
passed for `$0.153232781` in generation plus repair calls. The remaining rows
are not all ordinary proof-repair cases: `det_triangular`,
`simpleTransposition_sq_eq_one`, and the repaired `summable_fps_comp` are
statement-family/context-selection misses.

## Balanced-Span Paid Rerun

After adding bounded TeX environment expansion, a fresh 11-record source-only
generation run was executed:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run python scripts/run_source_statement_live_eval.py \
  --records docs/source-statement-runs/2026-05-05-preflight-passing-11-generation/eval/selected-records.jsonl \
  --output docs/source-statement-runs/2026-05-05-preflight-passing-11-source-only-balanced-generation \
  --limit 11 --sample-mode corpus-spread --include-record-imports \
  --lake-cache-from algebraic-combinatorics --generation-only \
  --context-mode source-only \
  --max-actual-cost-usd 0.40 --concurrency 3 \
  --max-tokens 32768 --reasoning-effort high
```

Result:

- paid calls: `11`
- generation cost: `$0.126677307`
- usable generated declarations: `10/11`
- rejected for forbidden placeholder: `1/11`
- hidden-grader verification: `1/11`

The pass was again the FPS `X_mul`/shift row. The balanced span changed row 11
from an order-two theorem to a transposition-equality theorem, then a
visible-context shape repair changed it to the correct `IsSwap` statement shape.
That repair still did not compile because the generated proof could not prove
the `Fin n` bound for `i.val + 1`.

Shape-warning repairs:

- repair attempt 1 targeted rows 7 and 11 from visible diagnostics; cost:
  `$0.010895358`; result: `0/2` passed.
- repair attempt 2 targeted row 11's missing-helper compiler error; cost:
  `$0.003953889`; result: `0/1` passed.
- repair attempt 3 targeted row 11's direct-constructor proof after the `Fin n`
  bound failure; cost: `$0.005651752`; result: `0/1` passed. The remaining
  compiler error is a brittle distinctness proof that uses `Nat.succ_ne_self`
  in the wrong equality direction.

Takeaway: environment balancing is a real context-selection fix, but this
11-row slice still does not mostly succeed. The next gains should come from
better source target selection and local API retrieval, not trust scoring.

## Source-Span Balance Fix

The row 11 failure exposed a concrete source-selection bug. The source-only
prompt for `simpleTransposition_isSwap` ended at `\begin{proposition}` before
the proposition body, so the model saw the definition/example context but not
the proposition body. `tex_source_focus` now tracks balanced TeX environments
and emits span risks such as:

- `snippet_ends_with_unclosed_environment:proposition`
- `snippet_starts_after_environment_begin:definition`

The source snippet loader now also expands TeX line ranges backward/forward,
within a bounded window, to include missing environment begins and ends. In the
regenerated 11-record source-only budget artifact, row 11 expands from
`256-278` to `255-290` with adjustment reasons:

- `expanded_backward_to_include_environment_begin`
- `expanded_forward_to_close_environment`

This is still not a guarantee that the source span picks the same theorem
family as the withheld Lean target, but it removes one concrete failure mode:
paid prompts should not stop immediately before a proposition body.

## What Changed In The Prompt

In `source-only` mode:

- `target_source_focus.target_declaration_source_comment` is `null`;
- `target_source_focus.record_comment_labels` is empty;
- `specific_source_labels` and `specific_labeled_parts` are not inferred from
  target-derived comments;
- hidden target declaration names are not used for domain-guidance triggers;
- imported declarations found only by matching source labels are not injected.
- earlier same-file declarations whose visible doc comments contain source-span
  labels are injected as `Same-file source-label API` blocks, as long as they
  appear before the withheld target declaration.
- `tex_source_focus` is added from the visible TeX/source span, including
  declared labels, referenced labels, theorem-like environments, source-keyword
  cues, part markers that are not merely inline `\ref{...} \textbf{(b)}`
  references, and broad-span risk flags.

This intentionally makes some prompts less helpful. For example, the
`fps_comp_coeff_finite` source-only prompt sees the source span label
`def.fps.subs`, but not the target doc-comment phrase “alternative coefficient
formula”. As a result, it does not receive the finite-coefficient
`finsum_eq_sum_of_support_subset` hint that the target-comment prompt received.
That is the point of this mode: it exposes where realistic context selection
needs to infer focus from TeX/source segmentation rather than from the target
Lean artifact.

After adding same-file source-label API retrieval, the regenerated row 11
source-only budget payload includes:

- `simpleTransposition_eq_transposition`
- `simpleTransposition_apply_self`
- `simpleTransposition_apply_succ`

These are prior declarations in the same file with visible source-label
comments. This is a generic context-selection improvement: it does not inspect
the withheld target declaration, and it only uses labels already present in the
selected source span.

## Tests

Focused tests passed:

```bash
UV_CACHE_DIR=/tmp/uv-cache-repoprover uv run pytest \
  tests/test_source_statement_live_eval.py \
  tests/test_source_statement_generation_artifacts.py
```

Result: `61 passed`.
After adding TeX-derived focus extraction, the same focused test set passes
with `63 passed`.
After tightening the X-shift prompt/diagnostic distinction, the focused test set
passes with `65 passed`.
After adding targeted verifier indices for repair artifacts, the focused test
set passes with `66 passed`.
After adding TeX environment-balance span risks, the focused test set passes
with `67 passed`. After adding bounded TeX span expansion, it passes with
`68 passed`. After adding visible `IsSwap` diagnostics and missing-helper
repair guidance, it passes with `70 passed`. The final repair-guidance update
keeps that same focused suite green with `70 passed`. After adding same-file
source-label API retrieval, it passes with `71 passed`.

## Next Step

Use `source-only` as the default for realistic validation. The next work should
not be another hand-tuned six-row repair loop. It should improve TeX/source
focus selection for rows where the selected source span is too broad, begins or
ends inside theorem-like environments, or points at the wrong theorem family,
then rerun a small paid broader-slice validation.
