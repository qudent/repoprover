import Mathlib

open scoped BigOperators
open Finset Nat

/-!
Post-hoc diagnostic only.

The generator saw source text plus checked Mathlib context, not the aligned
gold theorem below. This file demonstrates that the generated range-sum
Vandermonde theorem implies the aligned antidiagonal gold surface once the
checked bridge fact is used. The current semantic-coverage grader does not
count this automatically because it only tries `simpa using`.
-/

theorem generated_vandermonde_nat (a b n : ℕ) :
    (a + b).choose n = ∑ k ∈ range (n + 1), a.choose k * b.choose (n - k) := by
  calc
    (a + b).choose n = ∑ ij ∈ antidiagonal n, a.choose ij.1 * b.choose ij.2 := by
      rw [Nat.add_choose_eq]
    _ = ∑ k ∈ range (n + 1), a.choose k * b.choose (n - k) := by
      rw [Finset.Nat.sum_antidiagonal_eq_sum_range_succ (fun i j => a.choose i * b.choose j) n]

theorem gold_antidiagonal_from_generated (a b n : ℕ) :
    (a + b).choose n = ∑ ij ∈ antidiagonal n, a.choose ij.1 * b.choose ij.2 := by
  calc
    (a + b).choose n = ∑ k ∈ range (n + 1), a.choose k * b.choose (n - k) :=
      generated_vandermonde_nat a b n
    _ = ∑ ij ∈ antidiagonal n, a.choose ij.1 * b.choose ij.2 := by
      rw [← Finset.Nat.sum_antidiagonal_eq_sum_range_succ (fun i j => a.choose i * b.choose j) n]
