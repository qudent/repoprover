# Minimal-Context Pilot Review

Records reviewed: 4 from `docs/minimal-context-generated-records.jsonl`.
Reviewer model: `qwen/qwen3-coder`.
Run timestamp: `2026-04-28T12:14:44.945195+00:00`.
Token usage: 10,681 prompt / 1,505 completion.
Estimated OpenRouter cost: `$0.005059`.

## Findings

### ac-notations-and-elementary-facts-examples:binom_neg_one

- Verdict: `revise` (2,071 prompt / 340 completion, $0.001068).
- Source span: Insufficiently detailed for Lean formalization; lacks explicit mention of Ring.choose or coercion handling.
- Lean context: Includes necessary lemmas but omits key imports and lacks clarity on required coercions.
- Missing context:
  - Missing import: 'import Mathlib.Algebra.Ring.Choose'
  - Missing import: 'import Mathlib.Data.Int.Pow'
  - Missing explicit mention of coercion handling in source or context
- Oversized context:
  - mathlib_context includes 'ring tactic for simplifying integer expressions' which is too vague and not a Mathlib fact
- Recommended edits:
  - Add explicit imports for Ring.choose and Int.Pow
  - Clarify in source_span or notes that coercion handling is essential
  - Remove vague tactic descriptions from mathlib_context
- Review notes:
  - Source span does not explicitly indicate the need for Ring.choose API or coercion handling, which are critical for Lean formalization.
  - The mathlib_context includes a vague tactic reference that should be removed.
  - Missing explicit imports prevent immediate reproducibility of the Lean output.
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.5, "model_extraction": 0.4, "source_span": 0.4}`

### ac-notations-and-elementary-facts-examples:binom_factorial_formula

- Verdict: `revise` (1,840 prompt / 305 completion, $0.000954).
- Source span: Insufficiently precise; lacks Lean-specific formalization details
- Lean context: Missing explicit dependency and constraint formalization
- Missing context:
  - Explicit dependency on `Nat.choose_eq_factorial_div_factorial` in Lean context
  - Formalization of the constraint `k ≤ n` in Lean context
- Recommended edits:
  - Add `Nat.choose_eq_factorial_div_factorial` to `mathlib_context`
  - Include assumption `k ≤ n` in Lean context or ensure it is derivable
- Review notes:
  - The source span provides the mathematical statement but lacks Lean-specific elements like precise theorem names and explicit dependencies.
  - Lean output depends on `Nat.choose_eq_factorial_div_factorial` which is not included in the current context.
  - The assumption `k ≤ n` is critical and must be included in the Lean context.
- Trust updates: `{"human_review": 0.3, "lean_dependency_graph": 0.55, "model_extraction": 0.45, "source_span": 0.65}`

### ac-notations-and-elementary-facts-examples:prod_odd_eq_doubleFactorial

- Verdict: `reject` (3,090 prompt / 400 completion, $0.001400).
- Source span: Insufficient for double factorial definition or inductive proof structure.
- Lean context: Missing core Lean definitions and lemmas required for the proof.
- Missing context:
  - Definition of double factorial (n!! or `doubleFactorial` in Lean)
  - Lemma `doubleFactorial_add_two` which is central to the inductive step
  - Inductive proof pattern for product ranges
  - Lean tactics: `omega`, `ring`, `native_decide` usage not derivable from TeX
- Recommended edits:
  - Include the definition of double factorial in source or mathlib_context
  - Add `doubleFactorial_add_two` and related recurrence lemmas to mathlib_context
  - Clarify that the TeX example motivates but does not define the necessary Lean machinery
- Review notes:
  - The TeX source introduces the product of odd numbers but lacks formal definition of double factorial or recurrence properties.
  - The Lean proof critically depends on `doubleFactorial_add_two` which is neither in the source nor derivable from it.
  - Tactic usage (`omega`, `ring`, `native_decide`) is specific to Lean and not inferable from the TeX context.
  - The record's mathlib_context mentions `doubleFactorial_add_two` but it is not justified by the source_span or TeX content.
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.3, "model_extraction": 0.2, "source_span": 0.4}`

### ac-notations-and-elementary-facts-examples:factorial_dvd_prod_odd_mul_pow

- Verdict: `revise` (3,680 prompt / 460 completion, $0.001638).
- Source span: Insufficient detail for Lean formalization; omits indexing, double factorial usage, and divisibility properties.
- Lean context: Missing key Lean lemmas like prod_odd_eq_doubleFactorial and factorial_two_mul' which are used in the proof.
- Missing context:
  - prod_odd_eq_doubleFactorial (used in line 258)
  - factorial_two_mul' (used in line 246)
  - doubleFactorial_two_mul (used in line 246)
  - Nat.doubleFactorial definition and its relationship to products of odd numbers
  - Finset.range usage for indexing the product of odd numbers
  - factorial_mul_factorial_dvd_factorial theorem (used in line 251)
- Recommended edits:
  - Add the Lean declarations 'prod_odd_eq_doubleFactorial' and 'factorial_two_mul'' to lean_predecessors with their respective paths and reasons.
  - Include 'Nat.doubleFactorial' and 'Finset.range' in mathlib_context with explanations of their roles.
  - Expand source_spans to include more detailed explanation of the product indexing and double factorial usage.
- Review notes:
  - The TeX source does not explicitly mention the use of double factorial or Finset.range, which are crucial for the Lean proof.
  - The Lean output uses specific lemmas like 'prod_odd_eq_doubleFactorial' and 'factorial_two_mul'' that are not included in the minimal context.
  - The proof relies on 'doubleFactorial_two_mul' and 'factorial_mul_factorial_dvd_factorial' which are missing from the context.
- Trust updates: `{"human_review": 0.0, "lean_dependency_graph": 0.3, "model_extraction": 0.2, "source_span": 0.4}`
