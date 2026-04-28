# Minimal-Context Pilot Review

Records reviewed: 10 from `docs/minimal-context-generated-records-batch2.jsonl`.
Reviewer model: `qwen/qwen3-coder`.
Run timestamp: `2026-04-28T15:57:43.537273+00:00`.
Token usage: 20,187 prompt / 3,573 completion.
Estimated OpenRouter cost: `$0.010873`.

## Findings

### ac-notations-and-elementary-facts-examples:binom_two_n_n_eq

- Verdict: `revise` (3,650 prompt / 377 completion, $0.001482).
- Source span: Insufficient TeX details for Lean proof steps
- Lean context: Missing key lemma and explicit division handling
- Missing context:
  - Nat.succ_mul_centralBinom_succ recurrence relation
  - factorial_dvd_prod_odd_mul_pow divisibility lemma
  - Dvd.intro for handling divisibility in ℕ
  - Nat.div_eq_iff_eq_mul_left for division rewriting
  - Nat.mul_div_cancel_left for factorial simplification
- Recommended edits:
  - Add Nat.succ_mul_centralBinom_succ to mathlib_context
  - Add factorial_dvd_prod_odd_mul_pow to lean_predecessors with reason about divisibility
  - Include Dvd.intro and Nat.div_eq_iff_eq_mul_left in mathlib_context for division handling
  - Add Nat.mul_div_cancel_left to mathlib_context for factorial simplifications
- Review notes:
  - TeX proof uses algebraic manipulation while Lean uses induction with specific lemmas
  - Missing explicit mention of recurrence and divisibility lemmas in TeX
  - Lean requires explicit division handling in ℕ which TeX omits
  - Source span trust reduced due to missing Lean-specific proof details
  - Lean dependency graph trust reduced due to missing key lemmas
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.3, "model_extraction": 0.2, "source_span": 0.4}`

### ac-notations-and-elementary-facts-examples:pascal_identity

- Verdict: `revise` (1,922 prompt / 348 completion, $0.001049).
- Source span: Insufficiently precise; states identity for 'any numbers m and n' but Lean restricts to natural numbers with positivity conditions.
- Lean context: Missing explicit mention of Nat subtraction edge case handling and precise Mathlib lemma name in source or context.
- Missing context:
  - Explicit mention in source or context of the Mathlib lemma `Nat.choose_eq_choose_pred_add`
  - Clarification in source or context that the identity is restricted to natural numbers with m,n > 0 due to Nat subtraction behavior
- Recommended edits:
  - Update source span to clarify that the identity is restricted to natural numbers and requires m,n > 0
  - Add explicit mention of `Nat.choose_eq_choose_pred_add` in mathlib_context or as a predecessor
- Review notes:
  - Mismatch between TeX formulation ('any numbers m and n') and Lean implementation (natural numbers with positivity constraints).
  - Lean-specific edge case handling with Nat subtraction not reflected in source span.
  - Mathlib lemma name `Nat.choose_eq_choose_pred_add` is critical context but missing from both source and minimal context.
- Trust updates: `{"human_review": 0.3, "lean_dependency_graph": 0.55, "model_extraction": 0.45, "source_span": 0.4}`

### ac-notations-and-elementary-facts-examples:pascal_identity_ring

- Verdict: `revise` (2,148 prompt / 385 completion, $0.001166).
- Source span: insufficiently specific to TeX's generality claim
- Lean context: missing critical dependencies and assumptions
- Missing context:
  - Ring.choose_succ_succ (critical Mathlib lemma used in proof)
  - Nat.succ_pred_eq_of_pos (used for decrementing n)
  - Nat.sub_add_cancel (used in final simplification)
  - Nat.pred_eq_sub_one (used in rewriting)
  - specific subtraction behavior in rings (m = (m - 1) + 1)
- Recommended edits:
  - Add Ring.choose_succ_succ to mathlib_context
  - Add Nat.succ_pred_eq_of_pos to mathlib_context
  - Add Nat.sub_add_cancel to mathlib_context
  - Add Nat.pred_eq_sub_one to mathlib_context
  - Add comment about ring subtraction property to source_span reasoning
- Review notes:
  - Source span does not justify the specific Lean formulation - TeX claims 'any numbers m and n' but Lean requires structured assumptions
  - Missing key Mathlib dependency Ring.choose_succ_succ which is explicitly referenced in the proof
  - Critical natural number handling lemmas missing from context (Nat.succ_pred_eq_of_pos, Nat.sub_add_cancel)
  - The proof relies on specific ring subtraction properties not captured in current context
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.3, "model_extraction": 0.2, "source_span": 0.4}`

### ac-notations-and-elementary-facts-examples:pascal_identity_succ

- Verdict: `reject` (1,867 prompt / 339 completion, $0.001021).
- Source span: Insufficient TeX context for Lean formalization
- Lean context: Missing critical Mathlib API and typeclass assumptions
- Missing context:
  - Definition of generalized binomial coefficient `Ring.choose`
  - Mathlib theorem `Ring.choose_succ_succ`
  - Typeclass assumptions `[CommRing R] [BinomialRing R] [NatPowAssoc R]`
- Recommended edits:
  - Add explicit definition of `Ring.choose` in source context
  - Include statement of `Ring.choose_succ_succ` in source or Mathlib context
  - Add typeclass assumptions `[CommRing R] [BinomialRing R] [NatPowAssoc R]` to source context
- Review notes:
  - The TeX source provides only the classical Pascal identity but lacks the generalized ring-theoretic context needed for the Lean formalization
  - The Lean output uses `Ring.choose` and `Ring.choose_succ_succ` which are not derivable from the provided TeX context
  - Critical typeclass assumptions are missing from both source and Mathlib context
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.2, "model_extraction": 0.1, "source_span": 0.3}`

### ac-notations-and-elementary-facts-examples:pascal_identity_int

- Verdict: `revise` (1,918 prompt / 360 completion, $0.001070).
- Source span: Mismatch between TeX generality and Lean constraints
- Lean context: Missing explicit reference to `Ring.choose` definition and API
- Missing context:
  - Definition and properties of `Ring.choose`
  - Explicit statement or import of `pascal_identity_ring`
  - Mathlib's `data.int.choose` or equivalent for integer binomial coefficients
- Line or label issues:
  - TeX source span does not match Lean's type constraints (ℕ vs ℤ, positivity condition)
- Recommended edits:
  - Add explicit Mathlib import for `Ring.choose` definition
  - Include `pascal_identity_ring` in Mathlib context or predecessors
  - Clarify that TeX proposition is generalized in Lean with explicit types
- Review notes:
  - TeX source uses standard binomial notation but Lean uses `Ring.choose` - this transition is not documented
  - Lean version has stronger type constraints (n : ℕ, 0 < n) not reflected in TeX
  - Record claims TeX introduces the formal counterpart but TeX lacks Lean-specific details like Ring.choose
  - Missing explicit dependency on `pascal_identity_ring` in context despite output line citing it
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.3, "model_extraction": 0.2, "source_span": 0.4}`

### ac-notations-and-elementary-facts-examples:pascal_identity_rat

- Verdict: `revise` (1,919 prompt / 329 completion, $0.001014).
- Source span: Insufficient TeX context for Lean formalization due to missing Lean-specific details.
- Lean context: Missing essential Lean predecessor and Mathlib API context.
- Missing context:
  - Ring.choose API not mentioned in TeX or minimal context
  - pascal_identity_ring theorem not derivable from provided TeX
  - Type coercion subtleties (ℕ to ℚ) not indicated in TeX
- Recommended edits:
  - Add explicit mention of `Ring.choose` in source_span or mathlib_context
  - Include `pascal_identity_ring` theorem in source_span or predecessor context
  - Clarify the shift from general numbers in TeX to ℚ and ℕ in Lean
- Review notes:
  - TeX source introduces Pascal's identity but omits Lean-specific formalization details like `Ring.choose`.
  - Lean output depends on `pascal_identity_ring` which is not derivable from the TeX source alone.
  - Trust scores reduced due to missing critical context for reproducing Lean output.
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.3, "model_extraction": 0.3, "source_span": 0.3}`

### ac-notations-and-elementary-facts-examples:binom_zero_of_lt

- Verdict: `provisionally_accept` (1,610 prompt / 294 completion, $0.000883).
- Source span: Adequate TeX proposition provided with clear statement and label.
- Lean context: Minimal context includes necessary import and Mathlib fact; however, notation mapping is not explicitly justified.
- Missing context:
  - Explicit mention or explanation of the `.choose` notation in Lean corresponding to TeX’s \dbinom{m}{n}
- Recommended edits:
  - Add a note clarifying that m.choose n in Lean corresponds to \binom{m}{n} in TeX
- Review notes:
  - The source span correctly identifies the proposition being formalized.
  - Lean output aligns with the TeX statement and uses a known Mathlib lemma.
  - Trust scores are appropriately conservative for model-generated data.
  - Notation mapping between TeX and Lean should be made explicit for full clarity.
- Trust updates: `{"human_review": 0.3, "lean_dependency_graph": 0.55, "model_extraction": 0.45, "source_span": 0.65}`

### ac-notations-and-elementary-facts-examples:binom_symm

- Verdict: `revise` (1,787 prompt / 430 completion, $0.001167).
- Source span: Insufficient TeX context for Lean formalization due to mismatch in domain assumptions and missing Lean-specific details
- Lean context: Mathlib context is incomplete; source spans do not justify the use of Nat.choose_symm or Eq.symm
- Missing context:
  - Nat.choose_symm requires k ≤ n hypothesis which is not stated in TeX
  - Eq.symm usage for flipping equality direction not indicated in TeX
  - TeX states k ∈ ℝ but Lean uses k : ℕ, requiring truncation or reinterpretation not present in source
- Line or label issues:
  - The source span line_range [154, 161] labeled 'thm.binom.sym' does not match the precise statement needed for Lean (which requires k ≤ n and k : ℕ)
- Recommended edits:
  - Narrow source_span line_range to exclude misleading generality (k ∈ ℝ), or add note about necessary reinterpretation
  - Add explicit mention of Nat.choose_symm and its hypothesis k ≤ n to mathlib_context
  - Include Eq.symm in mathlib_context as it's directly used in the proof
- Review notes:
  - TeX source claims k ∈ ℝ but Lean requires k : ℕ with hypothesis k ≤ n; this discrepancy makes the source_span misleading without reinterpretation
  - Lean output directly applies Nat.choose_symm and Eq.symm but neither is derivable from the TeX as given
  - The mismatch between source and target contexts indicates a failure of minimal sufficiency
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.3, "model_extraction": 0.2, "source_span": 0.3}`

### ac-notations-and-elementary-facts-examples:binom_symm_add

- Verdict: `reject` (1,662 prompt / 366 completion, $0.001024).
- Source span: Insufficiently specific to justify Lean output
- Lean context: Missing key Lean API and notation context
- Missing context:
  - The precise statement being formalized: (a + b).choose a = (a + b).choose b
  - Nat type constraint in the theorem signature
  - Lean's Nat.choose notation and its binding power
  - The specific Mathlib lemma Nat.choose_symm_add being applied
- Recommended edits:
  - Add the exact Lean theorem statement to source_spans for proper context
  - Include Nat.choose_symm_add in mathlib_context with explanation of its role
  - Add Nat type notation context to lean_predecessors or mathlib_context
  - Clarify that the TeX source does not contain the specific identity being formalized
- Review notes:
  - The TeX source discusses general binomial symmetry but does not state the specific case (a+b).choose a = (a+b).choose b
  - Lean output requires explicit knowledge of Nat.choose notation and Nat.choose_symm_add lemma
  - Record lacks the precise mathematical statement being formalized
  - Missing critical context about Lean's Nat type and choose notation binding
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.2, "model_extraction": 0.1, "source_span": 0.3}`

### ac-notations-and-elementary-facts-examples:binom_symm_of_eq_add

- Verdict: `reject` (1,704 prompt / 345 completion, $0.000996).
- Source span: Insufficiently specific to justify Lean formulation
- Lean context: Missing key Mathlib dependencies and Lean-specific notation
- Missing context:
  - Nat.choose_symm_of_eq_add (specific Mathlib lemma used in proof)
  - n.choose notation definition in Lean
  - ℕ type constraints and their implications in Lean
- Recommended edits:
  - Add explicit mention of Nat.choose_symm_of_eq_add in mathlib_context
  - Include n.choose notation in mathlib_context
  - Clarify that the source span provides conceptual but not formal justification
- Review notes:
  - Source span discusses binomial coefficient symmetry but in general form (n choose k = n choose (n-k)), not the specific additive decomposition form (n = a + b implies n choose a = n choose b) used in Lean
  - The Lean theorem name and proof reference Nat.choose_symm_of_eq_add which is not derivable from the provided TeX source alone
  - Missing context includes Lean-specific notation (n.choose) and type constraints (ℕ) that are essential for formal statement
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.2, "model_extraction": 0.1, "source_span": 0.3}`
