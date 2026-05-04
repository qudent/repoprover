# DeepSeek Source-Statement Prompt Findings

Date: 2026-05-04

## Objective

Find a prompt shape for `deepseek/deepseek-v4-pro` that makes the current
target-statement-withheld source-statement samples mostly generate compiling
Lean code.

## Best Current Prompt Shape

The best current prompt is implemented in `scripts/run_source_statement_live_eval.py`.
It keeps the target Lean statement and declaration name out of the model prompt,
but includes:

- selected TeX/source chunk and specific source-part focus metadata;
- Lean prefix context in source order;
- local notation support when the notation helper is not already in prefix
  context;
- local style/API examples from nearby previous declarations;
- current Lean/mathlib migration guidance, including:
  - avoid stale Lean 3 / old Mathlib names;
  - do not use `CommAlgebra`, `LaurentPolynomial.X`, guessed `*_apply`, or
    deprecated helper names unless displayed in context;
  - do not bundle typeclass objects into conjunctions;
  - use local PowerSeries coefficient order such as `coeff n f`;
  - use `LaurentPolynomial.T n` and local notation `K[T;T⁻¹]` for Laurent
    polynomial samples;
  - do not redeclare definitions or notation helpers already shown in prefix
    context;
  - apply existing theorem constants to their binders instead of using them
    bare.

For this sample, the successful recipe is not a single first-pass prompt. It is:

1. initial source-statement prompt with local API/migration guidance;
2. materialize the returned declaration with record-local imports enabled;
3. if the generated declaration fails before the grader, run one repair prompt
   that includes the original prompt context, the failed declaration, and the
   generated-only Lean error output. The repair prompt still withholds the
   grader-only target statement and target declaration name.

## Harness Fixes Needed Before The Prompt Could Be Measured

Two apparent DeepSeek failures were actually verifier/materializer issues:

- relative `--lake-cache-from algebraic-combinatorics` created broken relative
  `.lake/packages` symlinks inside `/tmp` projects; `copy_lake_cache` now
  resolves the cache source before symlinking;
- predecessor/context rendering duplicated declarations or carried detached doc
  blocks, making generated Lean files unparsable before the model output was
  meaningfully checked.

After fixing those, the two paid rows from
`/tmp/repoprover-source-statement-fixed-live-5-20260504T234006Z` were
rematerialized and Lean-checked successfully:

- `/tmp/repoprover-remat-live-record-001-current`: `det_transpose`;
- `/tmp/repoprover-remat-live-record-002-current`: `binom_factorial_formula`.

## Live Evidence

Current honest first-pass five-sample result: 2/5 successes.

The first two rows from the interrupted five-record run were originally marked
failed because of the relative cache symlink, but both pass under the fixed
materializer. The remaining three records were rerun twice after prompt/context
improvements:

- `/tmp/repoprover-source-statement-fixed-prompt-next3-20260504T235132Z`:
  0/3 successes, cost `$0.013164144`;
- `/tmp/repoprover-source-statement-local-examples-next3-20260504T235621Z`:
  0/3 successes, cost `$0.012040974`.

One generated-only compiler-feedback repair round was then run over those three
hard rows at `/tmp/repoprover-source-statement-repair-next3-20260505T001020Z`.
It repaired `FPS.X_coeff_one` successfully while still withholding the
grader-only gold statement from the repair prompt:

- repaired hard rows: 1/3 successes;
- repair cost: `$0.013255755`;
- combined sample result with one repair round: 3/5 successes.

Total paid cost in this prompt-debug slice was about `$0.0529`.

## Remaining Failure Modes

- `FPS.X_coeff_one`: first-pass DeepSeek still tends to over-generalize a
  definition into a stronger conjunction or use the wrong `coeff` application
  shape. The generated-only compiler-feedback repair prompt fixed one such
  output and the repaired declaration passed the hidden grader.
- `laurentPolynomial_T_mul_T_neg`: DeepSeek still formalizes the broad theorem
  text about Laurent polynomial algebra structure instead of the narrow target
  inverse formula. This likely needs either stronger source-label focus or a
  retrieval snippet showing the exact `LaurentPolynomial.T n * T (-n)` idiom.
- `monomialTableau_eq_xPow_content`: after duplicate-context cleanup, the
  prompt is cleaner. Enabling record-local imports fixes the missing
  `monomialExp` context, but first-pass and repaired outputs still need stronger
  type annotations around polymorphic `MvPolynomial` terms to avoid stuck
  typeclass metavariables.

## Conclusion

The current first-pass prompt is substantially better grounded than the original
migration guide-only prompt, but it does **not** make this sample mostly
compile. The evidence supports a 2/5 first-pass rate on the current five-sample
slice.

With record-local imports and one generated-only compiler-feedback repair prompt,
the same paid sample reaches 3/5. That is the first recipe in this run that
mostly generates correct compiling code for the sample, but the "mostly" claim
depends on the repair round, not on first-pass prompting alone.

The next productive step is to make the repair loop first-class and improve the
two remaining hard cases:

- make predecessor context self-contained across imported local files, or mark
  those records as requiring local-import context;
- add API retrieval snippets for domain-specific current Lean facts before the
  live call;
- add a deterministic local repair pass for near-miss generated theorem shapes.
