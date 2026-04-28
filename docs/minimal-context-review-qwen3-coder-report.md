# Minimal-Context Pilot Review

Records reviewed: 3 from `docs/minimal-context-pilot-records.jsonl`.
Reviewer model: `qwen/qwen3-coder`.
Run timestamp: `2026-04-28T11:18:47.088739+00:00`.
Token usage: 11,793 prompt / 1,350 completion.
Estimated OpenRouter cost: `$0.005024`.

## Findings

### ac-notations-and-elementary-facts-examples:basic-cardinality-principles

- Verdict: `revise` (3,326 prompt / 430 completion, $0.001506).
- Source span: Source lines cover the named principles but lack precise alignment with the Lean bijection principle's strengthened formulation.
- Lean context: Imports and Mathlib context are sufficient and minimal for the Lean output.
- Missing context:
  - The source span does not explicitly state the membership condition (hst) required in the Lean bijection principle.
  - The source does not mention the explicit function and bijective hypothesis formulation used in the Lean version.
- Recommended edits:
  - Add a note in the source span or review_notes indicating that the Lean bijection principle includes explicit function and membership hypotheses not present in the textbook wording.
  - Consider adding labels to the source span for better traceability to the Lean declarations.
- Review notes:
  - Generated from a cheap qwen/qwen3-coder extraction pass and then line-checked against raw GitHub excerpts.
  - Qwen reviewer 2026-04-28 verdict revise: source lines cover the named principles, but the Lean bijection statement strengthens the textbook wording into a finite-set API with explicit function and membership hypotheses.
  - Lean-checked on 2026-04-28: the output range builds with Mathlib.Data.Finset.Powerset and Mathlib.Data.Finset.Prod instead of all Mathlib.
  - No human review yet; keep as a failure-sensitive benchmark example rather than gold.
  - The source span lacks explicit mention of the function and membership conditions present in the Lean bijection principle.
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.55, "model_extraction": 0.35, "source_span": 0.3}`

### ac-notations-and-elementary-facts-examples:def.binom.binom

- Verdict: `provisionally_accept` (4,794 prompt / 303 completion, $0.001600).
- Source span: TeX spans cover the definition and a related factorial formula, matching the Lean content.
- Lean context: Mathlib context includes all direct dependencies used in the Lean proofs.
- Recommended edits:
  - Increase human_review trust score to reflect Lean-checked status and resolved neighbor-line leaks.
- Review notes:
  - Lean output builds successfully with Mathlib.RingTheory.Binomial, confirming import minimality.
  - All proof dependencies like Nat.cast_ne_zero, Nat.factorial_ne_zero, nsmul_eq_mul, and npow_one are present in mathlib_context.
  - TeX spans correctly align with the definition label def.binom.binom and related equation eq.binom.fac-form.
  - No oversized context detected; all Lean imports and Mathlib facts are directly used in the output range.
  - Previously noted trust issues about missing dependencies and neighbor lines have been resolved.
- Trust updates: `{"human_review": 0.6, "lean_dependency_graph": 0.7, "model_extraction": 0.5, "source_span": 0.5}`

### ac-notations-and-elementary-facts-examples:prop.binom.rec

- Verdict: `revise` (3,673 prompt / 617 completion, $0.001919).
- Source span: The source span includes the proposition and equation label but is slightly oversized with introductory citation.
- Lean context: Most context is appropriate but some Mathlib facts may be oversized; predecessor justification is incomplete.
- Missing context:
  - The source does not explicitly state the constraints on m and n (e.g., m > 0 when working over naturals), which are crucial for the Lean formalization and appear only in comments.
  - No explicit mention of the interpretation of binomial coefficients in the source (Nat.choose vs Ring.choose), which is critical for understanding the multiple variants in Lean.
- Oversized context:
  - Mathlib fact `Nat.choose_eq_choose_pred_add` is directly used in the first theorem but is not the most general form; however, it's needed for that specific variant.
  - The import `Mathlib.RingTheory.Binomial` might be oversized if more specific imports like `Mathlib.Algebra.BinomialRing` would suffice (requires checking).
  - The `NatPowAssoc` typeclass is included but its necessity is not clearly motivated in the source or comments.
- Line or label issues:
  - The line range [295, 346] correctly captures all five declarations, but the label `prop.binom.rec` refers to a single proposition in the source which is split into multiple Lean theorems with different assumptions.
- Recommended edits:
  - Narrow the source span to exclude the citation line (132) if it's not essential to the mathematical content.
  - Clarify in review_notes that the source proposition is generalized but Lean requires case distinctions by type, hence multiple theorems.
  - Add explicit note that the source does not state domain constraints (like m > 0) which are necessary for the natural number version and affect the formalization.
- Review notes:
  - The source proposition is generalized over 'any numbers m and n' but lacks explicit domain constraints, which are essential for the natural number case in Lean.
  - Lean formalization splits the general proposition into multiple typed variants due to differences in subtraction behavior and typeclass requirements (Nat vs Ring).
  - The predecessor `binom_def_formula` is noted as establishing notation, but its role in defining the correspondence between textbook and Lean binomial coefficients should be more explicit.
  - Some Mathlib facts like `NatPowAssoc` are included but their necessity or connection to the source is not clearly explained.
- Trust updates: `{"human_review": 0.6, "lean_dependency_graph": 0.5, "model_extraction": 0.3, "source_span": 0.3}`
