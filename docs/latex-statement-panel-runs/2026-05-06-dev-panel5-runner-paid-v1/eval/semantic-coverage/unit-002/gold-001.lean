/-
Copyright (c) Meta Platforms, Inc. and affiliates.
All rights reserved.
-/
import Mathlib

/-!
# Determinants: Basic Properties

This file formalizes the basic properties of determinants from
Section "Determinants" (sec.sign.det) of the source.

## Main definitions

The determinant is already defined in Mathlib as `Matrix.det`. This file provides:
* Additional lemmas connecting Mathlib's API to the textbook presentation
* Specific examples and exercises from the source

## Main results

### Definition (Definition def.det.det)
The determinant of an n×n matrix A is defined as:
  det A = ∑_{σ ∈ Sₙ} (-1)^σ · A_{1,σ(1)} · A_{2,σ(2)} · ... · A_{n,σ(n)}

### Basic Properties
* `Matrix.det_transpose` - Transposes preserve determinants (Theorem thm.det.transp)
* `Matrix.det_of_upperTriangular` / `Matrix.det_of_lowerTriangular` -
    Determinant of triangular matrix is product of diagonal (Theorem thm.det.triang)
* Row operation properties (Theorem thm.det.rowop):
  - (a) Swapping rows multiplies det by -1
  - (b) Zero row implies det = 0
  - (c) Equal rows implies det = 0
  - (d) Scaling a row by λ scales det by λ
  - (e,f) Adding multiple of one row to another preserves det
  - (g) Multilinearity in rows
* Column operation properties (Theorem thm.det.colop) - analogous for columns
* Permutation of rows/columns (Corollary cor.det.sig-row-col)
* `Matrix.det_mul` - Multiplicativity: det(AB) = det(A) · det(B) (Theorem thm.det.detAB)
* Row/column scaling (Corollary cor.det.scale-row-col)

### Propositions
* `det_xiyj_eq_zero` - det(xᵢyⱼ) = 0 for n ≥ 2 (Proposition prop.det.xiyj)
* `det_xi_add_yj_eq_zero` - det(xᵢ + yⱼ) = 0 for n ≥ 3 (Proposition prop.det.xi+yj)
* `det_hollow_matrix_eq_zero` - Hollow 5×5 matrix has det = 0 (Example exa.det.hollow5x5)

## References

* Source: BasicProperties.tex, sec.sign.det

## Implementation notes

Mathlib already provides `Matrix.det` with most of the basic properties.
This file adds:
1. Documentation connecting Mathlib API to the textbook
2. Specific examples and exercises from the source
3. Some additional lemmas in the style of the textbook

Note: Mathlib uses 0-indexing for matrices (Fin n), while the source uses 1-indexing.
The Mathlib definition uses A(σ(i), i) rather than A(i, σ(i)), but these are equivalent
by reindexing the permutation.
-/

open Matrix Finset BigOperators

namespace AlgebraicCombinatorics

namespace Det

variable {K : Type*} [CommRing K]
variable {n m : ℕ}

/-!
## Convention (conv.det.K)

We work over a commutative ring K. In most examples, K will be ℤ, ℚ, or a polynomial ring.
-/

/-!
## Convention (conv.det.matrices)

(a) For an n×m matrix A, A_{i,j} denotes the (i,j)-th entry.
(b) We write (a_{i,j})_{1≤i≤n, 1≤j≤m} for the matrix with entries a_{i,j}.
(c) K^{n×m} denotes the set of n×m matrices over K.
(d) A^T denotes the transpose of A.

In Mathlib:
- Matrices are `Matrix (Fin n) (Fin m) K`
- Entry access is `A i j` for `i : Fin n` and `j : Fin m`
- Transpose is `Matrix.transpose A` or `Aᵀ`
-/

/-!
## Definition of Determinant (Definition def.det.det)

The determinant of an n×n matrix A is:
  det A = ∑_{σ ∈ Sₙ} (-1)^σ · ∏_{i=1}^n A_{i,σ(i)}

In Mathlib, this is `Matrix.det A`, defined as:
  det A = ∑_{σ ∈ Sₙ} (-1)^σ · ∏_{i} A_{σ(i),i}

These are equivalent by substituting σ ↦ σ⁻¹.
-/

/-- The determinant formula from Definition def.det.det.
    Note: Mathlib uses A(σ(i), i) rather than A(i, σ(i)). -/
theorem det_eq_sum_sign_prod (A : Matrix (Fin n) (Fin n) K) :
    A.det = ∑ σ : Equiv.Perm (Fin n), Equiv.Perm.sign σ • ∏ i, A (σ i) i := by
  rw [Matrix.det_apply]

/-- Alternative form with A(i, σ(i)) matching the textbook.
    This is obtained by substituting σ ↦ σ⁻¹ in the Mathlib definition.

    This is the formalization of Definition def.det.det from the source:
    det A = ∑_{σ ∈ Sₙ} (-1)^σ · ∏_{i=1}^n A_{i,σ(i)}

    The Mathlib definition uses A(σ(i), i) rather than A(i, σ(i)), but these
    are equivalent by substituting σ ↦ σ⁻¹. -/
theorem det_eq_sum_sign_prod_textbook (A : Matrix (Fin n) (Fin n) K) :
    A.det = ∑ σ : Equiv.Perm (Fin n), Equiv.Perm.sign σ • ∏ i, A i (σ i) := by
  rw [Matrix.det_apply]
  -- Substitute σ ↦ σ⁻¹: since σ ↦ σ⁻¹ is a bijection on Sₙ, the sum is unchanged
  rw [← Equiv.sum_comp (Equiv.inv (Equiv.Perm (Fin n)))]
  congr 1
  ext σ
  congr 1
  · -- sign(σ⁻¹) = sign(σ)
    simp only [Equiv.inv_apply, Equiv.Perm.sign_inv]
  · -- ∏ i, A (σ⁻¹ i) i = ∏ i, A i (σ i) by reindexing via σ
    rw [← Equiv.prod_comp σ]
    simp

/-!
## Examples of small determinants

For n = 0: det() = 1 (empty product)
For n = 1: det(a) = a
For n = 2: det [[a, b], [a', b']] = a·b' - b·a'
For n = 3: The 6-term expansion over S₃
-/

/-- Determinant of 0×0 matrix is 1 -/
theorem det_fin_zero' (A : Matrix (Fin 0) (Fin 0) K) : A.det = 1 :=
  Matrix.det_isEmpty

/-- Determinant of 1×1 matrix is its single entry -/
theorem det_fin_one' (A : Matrix (Fin 1) (Fin 1) K) : A.det = A 0 0 :=
  Matrix.det_unique A

/-- Determinant of 2×2 matrix: ad - bc -/
theorem det_fin_two' (A : Matrix (Fin 2) (Fin 2) K) :
    A.det = A 0 0 * A 1 1 - A 0 1 * A 1 0 :=
  Matrix.det_fin_two A

/-- The determinant of the identity matrix is 1.
    This is a basic API lemma for working with determinants. -/
@[simp]
theorem det_one_eq_one : det (1 : Matrix (Fin n) (Fin n) K) = 1 :=
  Matrix.det_one

/-- The determinant of the zero matrix is 0 (for n ≥ 1).
    This is a basic API lemma for working with determinants.

    Note: For n = 0, the zero matrix is the empty matrix, and det(∅) = 1
    by convention (empty product). -/
@[simp]
theorem det_zero_eq_zero (hn : 0 < n) : det (0 : Matrix (Fin n) (Fin n) K) = 0 := by
  apply Matrix.det_eq_zero_of_row_eq_zero ⟨0, hn⟩
  intro j
  simp

/-!
## Example: Hollow 5×5 matrix (Example exa.det.hollow5x5)

A 5×5 matrix with a 3×3 block of zeros in the middle has determinant 0.
The proof uses the pigeonhole principle: any permutation must map some
element of {2,3,4} to {2,3,4}, hitting a zero entry.
-/

/-- Pigeonhole lemma: any permutation of Fin 5 must map some element of {1,2,3}
    to an element of {1,2,3}. This is because {1,2,3} has 3 elements but its
    complement {0,4} has only 2 elements. -/
private lemma exists_middle_to_middle (σ : Equiv.Perm (Fin 5)) :
    ∃ i : Fin 5, i.val ∈ ({1, 2, 3} : Set ℕ) ∧ (σ i).val ∈ ({1, 2, 3} : Set ℕ) := by
  let middle : Finset (Fin 5) := {⟨1, by omega⟩, ⟨2, by omega⟩, ⟨3, by omega⟩}
  let outer : Finset (Fin 5) := {⟨0, by omega⟩, ⟨4, by omega⟩}
  by_contra h
  push_neg at h
  have h1 : ∀ i ∈ middle, σ i ∈ outer := by
    intro i hi
    have hi' : i.val ∈ ({1, 2, 3} : Set ℕ) := by
      simp only [middle, mem_insert, mem_singleton] at hi
      rcases hi with rfl | rfl | rfl <;> simp
    specialize h i hi'
    simp only [outer, mem_insert, mem_singleton]
    have hlt : (σ i).val < 5 := (σ i).isLt
    interval_cases hv : (σ i).val
    · left; exact Fin.ext hv
    · exfalso; exact h (by simp : (1 : ℕ) ∈ ({1, 2, 3} : Set ℕ))
    · exfalso; exact h (by simp : (2 : ℕ) ∈ ({1, 2, 3} : Set ℕ))
    · exfalso; exact h (by simp : (3 : ℕ) ∈ ({1, 2, 3} : Set ℕ))
    · right; exact Fin.ext hv
  have h2 : (middle.image σ).card ≤ outer.card := by
    apply card_le_card
    intro x hx
    simp only [mem_image] at hx
    obtain ⟨i, hi, rfl⟩ := hx
    exact h1 i hi
  have h3 : (middle.image σ).card = middle.card := card_image_of_injective _ σ.injective
  have h4 : middle.card = 3 := by native_decide
  have h5 : outer.card = 2 := by native_decide
  omega

/-- A matrix with a "hollow core" of zeros has determinant zero.
    Label: exa.det.hollow5x5

    More precisely: if A_{i,j} = 0 whenever i, j ∈ {1, 2, 3} (0-indexed),
    then det A = 0. This is because any permutation σ must have some
    i ∈ {1,2,3} with σ(i) ∈ {1,2,3} by pigeonhole. -/
theorem det_hollow_core_eq_zero (A : Matrix (Fin 5) (Fin 5) K)
    (hA : ∀ i j : Fin 5, i.val ∈ ({1, 2, 3} : Set ℕ) → j.val ∈ ({1, 2, 3} : Set ℕ) →
      A i j = 0) : A.det = 0 := by
  rw [det_apply]
  apply Finset.sum_eq_zero
  intro σ _
  -- It suffices to show the product is zero
  suffices h : ∏ i, A (σ i) i = 0 by simp [h]
  -- By pigeonhole, there exists i with both i and σ(i) in the middle
  obtain ⟨i, hi_mid, hσi_mid⟩ := exists_middle_to_middle σ
  -- So A (σ i) i = 0
  apply Finset.prod_eq_zero (mem_univ i)
  exact hA (σ i) i hσi_mid hi_mid

/-!
## Proposition: det(xᵢyⱼ) = 0 (Proposition prop.det.xiyj)

For n ≥ 2, if we form the n×n matrix with (i,j)-entry xᵢ·yⱼ,
then its determinant is 0.

The proof uses ∑_{σ ∈ Sₙ} (-1)^σ = 0 for n ≥ 2.
-/

/-- The matrix with entries x_i * y_j.
    Label: prop.det.xiyj -/
def outerProductMatrix (x y : Fin n → K) : Matrix (Fin n) (Fin n) K :=
  Matrix.of fun i j => x i * y j

@[simp]
lemma outerProductMatrix_apply (x y : Fin n → K) (i j : Fin n) :
    outerProductMatrix x y i j = x i * y j := rfl

/-- Sum of signs over Sₙ is 0 for n ≥ 2.
    This is eq.cor.perm.num-even.sum-sign from the source.

    The proof uses a sign-reversing involution: multiply by a fixed transposition.
    For n ≥ 2, we can pick two distinct elements and their transposition t.
    Then σ ↦ t * σ pairs up permutations with opposite signs. -/
theorem sum_sign_eq_zero (hn : 2 ≤ n) :
    ∑ σ : Equiv.Perm (Fin n), (Equiv.Perm.sign σ : K) = 0 := by
  -- We use the involution σ ↦ σ * swap 0 1
  -- Since n ≥ 2, we can construct elements 0 and 1 in Fin n
  have hn0 : 0 < n := by omega
  have hn1 : 1 < n := by omega
  let i : Fin n := ⟨0, hn0⟩
  let j : Fin n := ⟨1, hn1⟩
  have hij : i ≠ j := by simp [i, j]
  let τ := Equiv.swap i j
  apply Finset.sum_involution (fun σ _ => σ * τ)
  · -- f a + f (g a ha) = 0
    intro σ _
    simp only [Equiv.Perm.sign_mul]
    have hτ : Equiv.Perm.sign τ = -1 := Equiv.Perm.sign_swap hij
    simp only [hτ, Units.val_mul, Units.val_neg, Units.val_one, Int.cast_mul, Int.cast_neg,
      Int.cast_one]
    ring
  · -- f a ≠ 0 → g a ≠ a
    intro σ _ _ hσ
    have : τ = 1 := by
      have := mul_left_cancel (a := σ) (b := σ * τ) (c := σ * 1) (by simp [hσ])
      simp at this
      exact this
    rw [Equiv.swap_eq_one_iff] at this
    exact hij this
  · -- g a ∈ s
    intro σ _
    exact mem_univ _
  · -- g (g a) = a
    intro σ _
    simp only [mul_assoc]
    rw [Equiv.swap_mul_self]
    simp

/-- Determinant of outer product matrix is 0 for n ≥ 2.
    Label: prop.det.xiyj -/
theorem det_outerProduct_eq_zero (x y : Fin n → K) (hn : 2 ≤ n) :
    (outerProductMatrix x y).det = 0 := by
  -- outerProductMatrix is the same as vecMulVec
  have h : outerProductMatrix x y = vecMulVec x y := rfl
  rw [h]
  -- Use Mathlib's det_vecMulVec which requires Nontrivial (Fin n)
  haveI : Nontrivial (Fin n) := Fin.nontrivial_iff_two_le.mpr hn
  exact det_vecMulVec x y

/-- Corollary: Matrix with all entries equal has det = 0 for n ≥ 2.
    Label: eq.prop.det.xiyj.cor-x -/
theorem det_const_matrix_eq_zero (c : K) (hn : 2 ≤ n) :
    (Matrix.of fun _ _ : Fin n => c).det = 0 := by
  have h : Nontrivial (Fin n) := Fin.nontrivial_iff_two_le.mpr hn
  convert det_vecMulVec (fun _ : Fin n => 1) (fun _ : Fin n => c)
  ext i j
  simp [vecMulVec]

/-!
## Proposition: det(xᵢ + yⱼ) = 0 (Proposition prop.det.xi+yj)

For n ≥ 3, if we form the n×n matrix with (i,j)-entry xᵢ + yⱼ,
then its determinant is 0.

The proof uses a cancellation argument involving transpositions.
-/

/-- The matrix with entries x_i + y_j.
    Label: prop.det.xi+yj -/
def sumMatrix (x y : Fin n → K) : Matrix (Fin n) (Fin n) K :=
  Matrix.of fun i j => x i + y j

@[simp]
lemma sumMatrix_apply (x y : Fin n → K) (i j : Fin n) :
    sumMatrix x y i j = x i + y j := rfl

/-- The matrix A in the factorization of sumMatrix: first column is x_i, second column is 1, rest are 0.
    Used in the second proof of prop.det.xi+yj. -/
def sumMatrix_factorA (x : Fin n → K) : Matrix (Fin n) (Fin n) K :=
  Matrix.of fun i j =>
    if j.val = 0 then x i
    else if j.val = 1 then 1
    else 0

/-- The matrix B in the factorization of sumMatrix: first row is 1, second row is y_j, rest are 0.
    Used in the second proof of prop.det.xi+yj. -/
def sumMatrix_factorB (y : Fin n → K) : Matrix (Fin n) (Fin n) K :=
  Matrix.of fun i j =>
    if i.val = 0 then 1
    else if i.val = 1 then y j
    else 0

/-- The matrix A in the factorization has a zero column when n ≥ 3 (column index 2). -/
lemma sumMatrix_factorA_has_zero_col (x : Fin n → K) (hn : 3 ≤ n) :
    ∀ i, (sumMatrix_factorA x) i ⟨2, by omega⟩ = 0 := by
  intro i
  simp only [sumMatrix_factorA, Matrix.of_apply]
  have h1 : ¬ (2 : ℕ) = 0 := by omega
  have h2 : ¬ (2 : ℕ) = 1 := by omega
  simp only [h1, ite_false, h2]

/-- The determinant of the factor matrix A is 0 when n ≥ 3. -/
lemma det_sumMatrix_factorA_eq_zero (x : Fin n → K) (hn : 3 ≤ n) :
    (sumMatrix_factorA x).det = 0 :=
  det_eq_zero_of_column_eq_zero ⟨2, by omega⟩ (sumMatrix_factorA_has_zero_col x hn)

/-- The matrix (x_i + y_j) factors as A * B where A = sumMatrix_factorA and B = sumMatrix_factorB. -/
lemma sumMatrix_eq_factorA_mul_factorB (x y : Fin n → K) (hn : 2 ≤ n) :
    sumMatrix x y = sumMatrix_factorA x * sumMatrix_factorB y := by
  ext i j
  simp only [sumMatrix, sumMatrix_factorA, sumMatrix_factorB, Matrix.of_apply, Matrix.mul_apply]
  conv_rhs =>
    arg 2
    ext k
    rw [show (if k.val = 0 then x i else if k.val = 1 then 1 else 0) *
            (if k.val = 0 then 1 else if k.val = 1 then y j else 0) =
        if k.val = 0 then x i else if k.val = 1 then y j else 0 by
      split_ifs <;> ring]
  have h0 : (⟨0, by omega⟩ : Fin n).val = 0 := rfl
  have h1 : (⟨1, by omega⟩ : Fin n).val = 1 := rfl
  let k0 : Fin n := ⟨0, by omega⟩
  let k1 : Fin n := ⟨1, by omega⟩
  have hne : k0 ≠ k1 := by
    intro h
    have : (0 : ℕ) = 1 := by simp only [k0, k1] at h; exact congrArg Fin.val h
    omega
  have hcalc : ∑ k : Fin n, (if k.val = 0 then x i else if k.val = 1 then y j else 0) = x i + y j := by
    calc ∑ k : Fin n, (if k.val = 0 then x i else if k.val = 1 then y j else 0)
        = (if k0.val = 0 then x i else if k0.val = 1 then y j else 0) +
          ∑ k ∈ univ.erase k0, (if k.val = 0 then x i else if k.val = 1 then y j else 0) := by
            rw [← Finset.add_sum_erase univ _ (Finset.mem_univ k0)]
        _ = x i + ∑ k ∈ univ.erase k0, (if k.val = 0 then x i else if k.val = 1 then y j else 0) := by
            simp only [k0, ite_true]
        _ = x i + ((if k1.val = 0 then x i else if k1.val = 1 then y j else 0) +
            ∑ k ∈ (univ.erase k0).erase k1, (if k.val = 0 then x i else if k.val = 1 then y j else 0)) := by
            rw [← Finset.add_sum_erase (univ.erase k0) _ (Finset.mem_erase.mpr ⟨hne.symm, Finset.mem_univ k1⟩)]
        _ = x i + (y j + ∑ k ∈ (univ.erase k0).erase k1, (if k.val = 0 then x i else if k.val = 1 then y j else 0)) := by
            simp only [k1]
            norm_num
        _ = x i + (y j + 0) := by
            congr 1
            congr 1
            apply Finset.sum_eq_zero
            intro k hk
            simp only [Finset.mem_erase, Finset.mem_univ, and_true] at hk
            have hk0 : k.val ≠ 0 := fun h => hk.2 (Fin.ext h)
            have hk1 : k.val ≠ 1 := fun h => hk.1 (Fin.ext h)
            simp only [hk0, ite_false, hk1]
        _ = x i + y j := by ring
  exact hcalc.symm

/-- Determinant of sum matrix is 0 for n ≥ 3.
    Label: prop.det.xi+yj

    The proof uses matrix factorization: (x_i + y_j) = A * B where A has a zero column. -/
theorem det_sumMatrix_eq_zero (x y : Fin n → K) (hn : 3 ≤ n) :
    (sumMatrix x y).det = 0 := by
  rw [sumMatrix_eq_factorA_mul_factorB x y (by omega : 2 ≤ n)]
  rw [det_mul]
  rw [det_sumMatrix_factorA_eq_zero x hn]
  ring


/-!
## Theorem: Transposes preserve determinants (Theorem thm.det.transp)

det(A^T) = det(A)
-/

/-- Transposes preserve determinants.
    Label: thm.det.transp -/
theorem det_transpose' (A : Matrix (Fin n) (Fin n) K) : Aᵀ.det = A.det :=
  det_transpose A

/-!
## Theorem: Determinants of triangular matrices (Theorem thm.det.triang)

If A is upper-triangular or lower-triangular, then det A = ∏ᵢ Aᵢᵢ.
-/

/-! RepoProver post-hoc semantic coverage check.
The aligned gold statement below is grader-only and was not shown to generation. -/

-- Generated declaration(s) under the original target file prefix context.
open Matrix

variable {K : Type*} [CommRing K] {n : ℕ}

theorem det_of_triangular (A : Matrix (Fin n) (Fin n) K) (h : A.BlockTriangular id ∨ A.BlockTriangular (OrderDual.toDual : Fin n → Fin n)) :
    A.det = ∏ i : Fin n, A i i := by
  rcases h with (hU | hL)
  · exact Matrix.det_of_upperTriangular hU
  · exact Matrix.det_of_lowerTriangular A hL

-- Grader-only check: original aligned statement proved from generated theorem(s).
/-- Determinant of upper triangular matrix is product of diagonal.
    Label: thm.det.triang -/
theorem __repoprover_latex_statement_check (A : Matrix (Fin n) (Fin n) K)
    (hA : ∀ i j, j < i → A i j = 0) : A.det = ∏ i, A i i := by
  first
  | simpa using det_of_triangular A h
  | simpa [Fintype.card_fin] using det_of_triangular A h
  | simpa using det_of_triangular A (by simpa [Fintype.card_fin] using h)
  | simpa [Fintype.card_fin] using det_of_triangular A (by simpa [Fintype.card_fin] using h)
  | simpa using det_of_triangular
  | simpa [Fintype.card_fin] using det_of_triangular
  | simpa using det_of_triangular A hA
  | simpa [Fintype.card_fin] using det_of_triangular A hA
  | simpa using det_of_triangular A (by simpa [Fintype.card_fin] using hA)
  | simpa [Fintype.card_fin] using det_of_triangular A (by simpa [Fintype.card_fin] using hA)
