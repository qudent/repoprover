# Minimal-Context Pilot Review

Records reviewed: 3 from `docs/minimal-context-pilot-records.jsonl`.
Reviewer model: `qwen/qwen3-coder`.
Run timestamp: `2026-04-28T11:08:43.121726+00:00`.
Token usage: 11,321 prompt / 1,298 completion.
Estimated OpenRouter cost: `$0.004827`.

## Findings

### ac-notations-and-elementary-facts-examples:basic-cardinality-principles

- Verdict: `revise` (3,230 prompt / 360 completion, $0.001359).
- Source span: Source span covers basic principles but lacks detail for bijection strengthening.
- Lean context: Lean context is minimal but sufficient for most theorems; missing explicit import paths.
- Missing context:
  - Missing explicit import paths for Mathlib theorems (e.g., `import Mathlib.Data.Finset.Card`)
  - Source does not explicitly mention the strengthened finite-set bijection API used in `bijection_principle` Lean statement
- Recommended edits:
  - Add explicit Mathlib import paths to `imports` or `mathlib_context`
  - Expand source span to include more detailed discussion of bijection principle if available, or note the discrepancy in review notes
- Review notes:
  - Generated from a cheap qwen/qwen3-coder extraction pass and then line-checked against raw GitHub excerpts.
  - Needs review: bijection_principle may need more context than the source paragraph because the Lean statement strengthens the textbook wording into a finite-set bijection API.
  - The source span does not fully justify the formalization of `bijection_principle`, which requires explicit handling of set membership and bijective function properties.
- Trust updates: `{"human_review": 0.2, "lean_dependency_graph": 0.35, "model_extraction": 0.35, "source_span": 0.35}`

### ac-notations-and-elementary-facts-examples:def.binom.binom

- Verdict: `revise` (4,626 prompt / 504 completion, $0.001925).
- Source span: Source spans cover the definition and a related factorial formula but lack explicit mention of key Mathlib API used in proofs.
- Lean context: Lean context imports Mathlib broadly and includes relevant Mathlib facts, but some dependencies like `npow_one` are missing.
- Missing context:
  - Missing import or explicit dependency on `npow_one` (used in `binom_one_right` proof).
  - Missing explicit mention in source spans of Mathlib's `Ring.choose_one_right'` which is directly used in the Lean output.
- Oversized context:
  - The import `Mathlib` is overly broad; should specify precise modules like `Mathlib.Algebra.CharZero.Defs`, `Mathlib.Data.Nat.Choose.Basic`, etc.
  - Some Mathlib facts listed (e.g., `Ring.choose_natCast`) may not be strictly necessary if their proofs are by exact reference and not used in intermediate reasoning.
- Recommended edits:
  - Add `npow_one` to `mathlib_context` or ensure it's available via explicit imports.
  - Explicitly mention `Ring.choose_one_right'` in the source context or LaTeX labels to justify its use.
  - Replace `imports: ["Mathlib"]` with specific Mathlib imports such as `Mathlib.Algebra.CharZero.Defs`, `Mathlib.Data.Nat.Factorial.Basic`, and `Mathlib.Algebra.Binomial.Core`.
- Review notes:
  - The record uses Mathlib lemmas like `Ring.choose_one_right'` and `npow_one` that are not justified by the current source spans or explicitly listed in the Lean context.
  - Importing all of Mathlib is not minimal; the context should be narrowed to only necessary modules.
  - Some listed Mathlib facts may be over-inclusive if they are used only via exact reference without local reasoning.
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.3, "model_extraction": 0.3, "source_span": 0.35}`

### ac-notations-and-elementary-facts-examples:prop.binom.rec

- Verdict: `revise` (3,465 prompt / 434 completion, $0.001544).
- Source span: insufficiently specific for Lean variants
- Lean context: missing local notation setup and some dependencies
- Missing context:
  - AlgebraicCombinatorics.FPS.binom_def_formula (establishes Ring.choose notation used in output)
  - NatPowAssoc class (used in ring variants but not declared in context)
  - Ring.choose_succ_succ (used directly in pascal_identity_succ and indirectly in others)
  - Nat.choose_eq_choose_pred_add (used directly in pascal_identity)
- Line or label issues:
  - source span lines 134-141 are too general; Lean output distinguishes natural, ring, integer, and rational variants not present in single source equation
- Recommended edits:
  - Add NatPowAssoc to lean_predecessors or imports
  - Clarify that source label 'prop.binom.rec' corresponds to multiple Lean theorems with different type assumptions
  - Include Ring.choose_succ_succ and Nat.choose_eq_choose_pred_add in mathlib_context since they are used directly
- Review notes:
  - The source span gives a general mathematical statement, but the Lean output contains multiple formalizations with different type constraints (Nat, Ring, Int, Rat). The minimal context should reflect this split.
  - The record mentions binom_def_formula as a predecessor but doesn't include NatPowAssoc which is required by several theorems.
  - Direct uses of Mathlib lemmas like Ring.choose_succ_succ and Nat.choose_eq_choose_pred_add should be listed in mathlib_context.
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.25, "model_extraction": 0.35, "source_span": 0.2}`
