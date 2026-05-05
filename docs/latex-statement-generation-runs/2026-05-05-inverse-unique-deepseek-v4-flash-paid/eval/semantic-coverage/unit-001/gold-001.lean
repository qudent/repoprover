/-
Copyright (c) Meta Platforms, Inc. and affiliates.
All rights reserved.
-/
/-
Copyright (c) 2025 AlgebraicCombinatorics contributors. All rights reserved.
Authors: AlgebraicCombinatorics contributors
-/
import Mathlib
import AlgebraicCombinatorics.DividingFPS

/-!
# Commutative Rings and Modules

This file provides the algebraic foundations for the theory of formal power series (FPS).
It corresponds to Section `\ref{sec.gf.defs}` and `\ref{subsec.gf.defs.commrings}` of the
source material (`CommutativeRings.tex`).

## Overview

Generating functions are not actually functions but *formal power series* (FPSs).
A formal power series is a "formal" infinite sum of the form `a₀ + a₁x + a₂x² + ⋯`,
where `x` is an indeterminate. Unlike analytic power series, we cannot substitute
numerical values for `x`.

This file reviews the algebraic structures needed for FPS:
- Commutative rings (Definition `def.alg.commring`)
- Modules over commutative rings (Definition `def.alg.module`)
- Inverses and fractions in commutative rings (`def.commring.inverse`, `def.commring.fracs`)

## Structure Note

The TeX source splits ring foundations across two files:
- `CommutativeRings.tex`: Definitions of commutative rings and modules
- `DividingFPS.tex`: Inverses, fractions, and FPS-specific division

This Lean file includes the general ring theory from both sources (inverses and fractions)
since they are foundational for all subsequent FPS theory. The FPS-specific content
(invertibility of power series, Newton's binomial formula, etc.) is in `DividingFPS.lean`.

Note: The definitions `IsInverse`, `IsInvertible`, and `fraction` here provide a pedagogical
bridge between the source's presentation and Mathlib's `IsUnit`, `Units`, etc. For actual
computations, prefer Mathlib's API directly.

## Main Definitions

### Definition def.alg.commring (Commutative Ring)

The source defines a commutative ring as a set K with three binary operations (⊕, ⊖, ⊙),
two distinguished elements (0 and 1), and nine axioms:
1. Commutativity of addition: a ⊕ b = b ⊕ a
2. Associativity of addition: a ⊕ (b ⊕ c) = (a ⊕ b) ⊕ c
3. Neutrality of zero: a ⊕ 0 = 0 ⊕ a = a
4. Subtraction undoes addition: a ⊕ b = c ↔ a = c ⊖ b
5. Commutativity of multiplication: a ⊙ b = b ⊙ a
6. Associativity of multiplication: a ⊙ (b ⊙ c) = (a ⊙ b) ⊙ c
7. Distributivity: a ⊙ (b ⊕ c) = (a ⊙ b) ⊕ (a ⊙ c) and (a ⊕ b) ⊙ c = (a ⊙ c) ⊕ (b ⊙ c)
8. Neutrality of one: a ⊙ 1 = 1 ⊙ a = a
9. Annihilation: a ⊙ 0 = 0 ⊙ a = 0

In Mathlib, this is captured by `CommRing K` (from `Mathlib.Algebra.Ring.Defs`).

### Definition def.alg.module (K-Module)

The source defines a K-module as a set M with addition, subtraction, scaling by K, and a
zero element, satisfying the standard module axioms.

In Mathlib, this is captured by `[AddCommGroup M] [Module K M]`.

### Definition def.commring.inverse (Inverses)

An element `a` of a commutative ring is **invertible** (a **unit**) if there exists `b`
with `a * b = 1`. The inverse is unique when it exists.

In Mathlib: `IsUnit a` and `Units L` (the type `Lˣ`).

### Definition def.commring.fracs (Fractions)

For an invertible element `a`, we write `b/a` for `b * a⁻¹`. Integer powers `a^n` are
defined for all `n ∈ ℤ` when `a` is invertible.

In Mathlib: `zpow` for integer powers on units.

## Main Results

Key properties of commutative rings mentioned in the source:
- `add_pow`: The binomial theorem `(a + b)^n = ∑ k, C(n,k) * a^k * b^(n-k)`
- `sub_pow`: Variant for subtraction
- Finite sums and products are well-defined and satisfy standard rules
- `isInverse_unique`: Inverses are unique (`thm.commring.inverse-uni`)

## Implementation Notes

The source defines commutative rings with explicit subtraction operation `⊖`.
Mathlib instead defines `Ring` with negation, and subtraction is derived as `a - b := a + (-b)`.
These definitions are equivalent:
- Given subtraction ⊖, define negation as `-a := 0 ⊖ a`
- Given negation, define subtraction as `a - b := a + (-b)`

The key theorem `commRing_sub_iff_add` below shows that Axiom 4 (subtraction undoes addition)
holds in Mathlib's formulation.

Similarly, the source defines modules with explicit subtraction, while Mathlib uses negation.
The equivalence is analogous.

## References

- Source: `AlgebraicCombinatorics/tex/FPS/CommutativeRings.tex`
- Additional source: `AlgebraicCombinatorics/tex/FPS/DividingFPS.tex` (inverses/fractions)
- Labels: `def.alg.commring`, `def.alg.module`, `def.commring.inverse`, `def.commring.fracs`
-/

namespace AlgebraicCombinatorics.FPS

/-!
## Section: Commutative Rings

A commutative ring is a set `K` equipped with operations `+`, `-`, `*` and elements `0`, `1`
satisfying the standard ring axioms with commutativity of multiplication.

In Mathlib, this is captured by the `CommRing` typeclass.
-/

section CommRingBasics

variable {K : Type*} [CommRing K]

/-- **Commutativity of addition** (Axiom 1 in def.alg.commring):
    `a + b = b + a` for all `a, b ∈ K`. -/
theorem commRing_add_comm (a b : K) : a + b = b + a := add_comm a b

/-- **Associativity of addition** (Axiom 2 in def.alg.commring):
    `a + (b + c) = (a + b) + c` for all `a, b, c ∈ K`. -/
theorem commRing_add_assoc (a b c : K) : a + (b + c) = (a + b) + c := (add_assoc a b c).symm

/-- **Neutrality of zero** (Axiom 3 in def.alg.commring):
    `a + 0 = a` for all `a ∈ K`. -/
theorem commRing_add_zero (a : K) : a + 0 = a := add_zero a

/-- **Neutrality of zero** (Axiom 3 in def.alg.commring):
    `0 + a = a` for all `a ∈ K`. -/
theorem commRing_zero_add (a : K) : 0 + a = a := zero_add a

/-- **Subtraction undoes addition** (Axiom 4 in def.alg.commring):
    `a + b = c ↔ a = c - b` for all `a, b, c ∈ K`. -/
theorem commRing_sub_iff_add (a b c : K) : a + b = c ↔ a = c - b := by
  constructor
  · intro h; rw [← h, add_sub_cancel_right]
  · intro h; rw [h, sub_add_cancel]

/-- **Commutativity of multiplication** (Axiom 5 in def.alg.commring):
    `a * b = b * a` for all `a, b ∈ K`. -/
theorem commRing_mul_comm (a b : K) : a * b = b * a := mul_comm a b

/-- **Associativity of multiplication** (Axiom 6 in def.alg.commring):
    `a * (b * c) = (a * b) * c` for all `a, b, c ∈ K`. -/
theorem commRing_mul_assoc (a b c : K) : a * (b * c) = (a * b) * c := (mul_assoc a b c).symm

/-- **Distributivity** (Axiom 7 in def.alg.commring):
    `a * (b + c) = a * b + a * c` for all `a, b, c ∈ K`. -/
theorem commRing_left_distrib (a b c : K) : a * (b + c) = a * b + a * c := mul_add a b c

/-- **Distributivity** (Axiom 7 in def.alg.commring):
    `(a + b) * c = a * c + b * c` for all `a, b, c ∈ K`. -/
theorem commRing_right_distrib (a b c : K) : (a + b) * c = a * c + b * c := add_mul a b c

/-- **Neutrality of one** (Axiom 8 in def.alg.commring):
    `a * 1 = a` for all `a ∈ K`. -/
theorem commRing_mul_one (a : K) : a * 1 = a := mul_one a

/-- **Neutrality of one** (Axiom 8 in def.alg.commring):
    `1 * a = a` for all `a ∈ K`. -/
theorem commRing_one_mul (a : K) : 1 * a = a := one_mul a

/-- **Annihilation** (Axiom 9 in def.alg.commring):
    `a * 0 = 0` for all `a ∈ K`. -/
theorem commRing_mul_zero (a : K) : a * 0 = 0 := mul_zero a

/-- **Annihilation** (Axiom 9 in def.alg.commring):
    `0 * a = 0` for all `a ∈ K`. -/
theorem commRing_zero_mul (a : K) : 0 * a = 0 := zero_mul a

end CommRingBasics

/-!
## Section: Examples of Commutative Rings

The source lists several examples of commutative rings:
- `ℤ`, `ℚ`, `ℝ`, `ℂ` are commutative rings
- `ℕ` is NOT a commutative ring (no subtraction), but is a commutative semiring
- `ℤ[√5]` is a commutative ring (subring of `ℝ`)
- `ℤ/m` is a commutative ring for any `m`
- Power set with symmetric difference is a Boolean ring
- The tropical semiring `ℤ ∪ {-∞}` with max and + operations

In Mathlib, these are available as instances:
- `CommRing ℤ`, `CommRing ℚ`, etc.
- `CommSemiring ℕ`
- `ZMod n` for `ℤ/n`
-/

section CommRingExamples

-- Standard number systems are commutative rings
example : CommRing ℤ := inferInstance
example : CommRing ℚ := inferInstance
example : CommRing ℝ := inferInstance
example : CommRing ℂ := inferInstance

-- ℕ is a commutative semiring (not a ring, since no subtraction)
example : CommSemiring ℕ := inferInstance

-- ℤ/m is a commutative ring (ZMod n in Mathlib)
example (n : ℕ) [NeZero n] : CommRing (ZMod n) := inferInstance

-- When p is prime, ℤ/p is a field
example (p : ℕ) [hp : Fact (Nat.Prime p)] : Field (ZMod p) := inferInstance

end CommRingExamples

/-!
## Section: Standard Rules in Commutative Rings

The source notes that in any commutative ring K, the standard rules of computation apply:
- Finite sums are well-defined (general associativity and commutativity)
- Finite products are well-defined
- Standard algebraic identities hold
- The binomial theorem: `(a + b)^n = ∑_{k=0}^n C(n,k) * a^k * b^(n-k)`
-/

section StandardRules

variable {K : Type*} [CommRing K]

/-- Negation distributes over addition: `-(a + b) = (-a) + (-b)`. -/
theorem neg_add_distrib (a b : K) : -(a + b) = -a + -b := neg_add a b

/-- Double negation: `-(-a) = a`. -/
theorem neg_neg_eq (a : K) : -(-a) = a := neg_neg a

/-- Scalar multiplication by integers distributes: `(n + m) • a = n • a + m • a`. -/
theorem add_zsmul_distrib (a : K) (n m : ℤ) : (n + m) • a = n • a + m • a := by rw [add_smul]

/-- Scalar multiplication by integers is associative: `(n * m) • a = n • (m • a)`. -/
theorem mul_zsmul_assoc (a : K) (n m : ℤ) : (n * m) • a = n • (m • a) := by rw [mul_smul]

/-- Multiplication distributes over subtraction: `a * (b - c) = a * b - a * c`. -/
theorem mul_sub_distrib (a b c : K) : a * (b - c) = a * b - a * c := mul_sub a b c

/-- Power of a product: `(a * b)^n = a^n * b^n`. -/
theorem mul_pow_eq (a b : K) (n : ℕ) : (a * b) ^ n = a ^ n * b ^ n := mul_pow a b n

/-- Power addition rule: `a^(n+m) = a^n * a^m`. -/
theorem pow_add_eq (a : K) (n m : ℕ) : a ^ (n + m) = a ^ n * a ^ m := pow_add a n m

/-- Power multiplication rule: `a^(n*m) = (a^n)^m`. -/
theorem pow_mul_eq (a : K) (n m : ℕ) : a ^ (n * m) = (a ^ n) ^ m := pow_mul a n m

/-- **The Binomial Theorem** (mentioned in def.alg.commring):
    `(a + b)^n = ∑_{k=0}^n C(n,k) * a^k * b^(n-k)`.

    In Mathlib, this is `add_pow` from `Mathlib.Data.Nat.Choose.Sum`. -/
theorem binomial_theorem (a b : K) (n : ℕ) :
    (a + b) ^ n = ∑ k ∈ Finset.range (n + 1), a ^ k * b ^ (n - k) * (n.choose k) :=
  add_pow a b n

/-- Variant of the binomial theorem with subtraction. -/
theorem binomial_theorem_sub (a b : K) (n : ℕ) :
    (a - b) ^ n = ∑ m ∈ Finset.range (n + 1), (-1) ^ (m + n) * a ^ m * b ^ (n - m) * n.choose m :=
  sub_pow a b n

end StandardRules

/-!
## Section: Modules over Commutative Rings

A K-module is a generalization of a vector space where the scalars come from a
commutative ring K (not necessarily a field).

The source defines a K-module (Definition `def.alg.module`) as a set M with:
- Addition `⊕ : M × M → M`
- Subtraction `⊖ : M × M → M`
- Scaling `⇀ : K × M → M`
- Zero element `0⃗ ∈ M`

satisfying the standard module axioms.

In Mathlib, this is captured by the `Module` typeclass, which requires:
- `AddCommGroup M` (for the additive structure)
- `Module K M` (for the scalar multiplication)
-/

section ModuleBasics

variable {K : Type*} [CommRing K]
variable {M : Type*} [AddCommGroup M] [Module K M]

/-- **Commutativity of addition** (Axiom 1 in def.alg.module):
    `a + b = b + a` for all `a, b ∈ M`. -/
theorem module_add_comm (a b : M) : a + b = b + a := add_comm a b

/-- **Associativity of addition** (Axiom 2 in def.alg.module):
    `a + (b + c) = (a + b) + c` for all `a, b, c ∈ M`. -/
theorem module_add_assoc (a b c : M) : a + (b + c) = (a + b) + c := (add_assoc a b c).symm

/-- **Neutrality of zero** (Axiom 3 in def.alg.module):
    `a + 0 = a` for all `a ∈ M`. -/
theorem module_add_zero (a : M) : a + 0 = a := add_zero a

/-- **Subtraction undoes addition** (Axiom 4 in def.alg.module):
    `a + b = c ↔ a = c - b` for all `a, b, c ∈ M`. -/
theorem module_sub_iff_add (a b c : M) : a + b = c ↔ a = c - b := by
  constructor
  · intro h; rw [← h, add_sub_cancel_right]
  · intro h; rw [h, sub_add_cancel]

/-- **Associativity of scaling** (Axiom 5 in def.alg.module):
    `u • (v • a) = (u * v) • a` for all `u, v ∈ K` and `a ∈ M`. -/
theorem module_smul_assoc (u v : K) (a : M) : u • (v • a) = (u * v) • a := by
  rw [mul_smul]

/-- **Left distributivity** (Axiom 6 in def.alg.module):
    `u • (a + b) = u • a + u • b` for all `u ∈ K` and `a, b ∈ M`. -/
theorem module_smul_add (u : K) (a b : M) : u • (a + b) = u • a + u • b := smul_add u a b

/-- **Right distributivity** (Axiom 7 in def.alg.module):
    `(u + v) • a = u • a + v • a` for all `u, v ∈ K` and `a ∈ M`. -/
theorem module_add_smul (u v : K) (a : M) : (u + v) • a = u • a + v • a := add_smul u v a

/-- **Neutrality of one** (Axiom 8 in def.alg.module):
    `1 • a = a` for all `a ∈ M`. -/
theorem module_one_smul (a : M) : (1 : K) • a = a := one_smul K a

/-- **Left annihilation** (Axiom 9 in def.alg.module):
    `0 • a = 0` for all `a ∈ M`. -/
theorem module_zero_smul (a : M) : (0 : K) • a = 0 := zero_smul K a

/-- **Right annihilation** (Axiom 10 in def.alg.module):
    `u • 0 = 0` for all `u ∈ K`. -/
theorem module_smul_zero (u : K) : u • (0 : M) = 0 := smul_zero u

/-!
### Additive Inverses and Subtraction

The source notes that most authors do not include subtraction in the definition of a K-module.
Instead, additive inverses can be constructed using scaling: the additive inverse of `a` is `(-1) • a`.
This shows that subtraction is derivable from the other operations.

In Mathlib, `AddCommGroup M` provides negation directly, and subtraction is defined as `a - b := a + (-b)`.
The following theorems show the equivalence between these approaches.
-/

/-- **Additive inverse via scaling** (Note in def.alg.module):
    The additive inverse of `a` can be constructed as `(-1) • a`.
    This shows why modules don't need explicit negation in their axioms. -/
theorem module_neg_eq_neg_one_smul (a : M) : -a = (-1 : K) • a := by
  rw [neg_one_smul]

/-- Subtraction can be expressed as addition of the negation. -/
theorem module_sub_eq_add_neg (a b : M) : a - b = a + (-b) := sub_eq_add_neg a b

/-- Subtraction can be expressed using scaling by `-1`. -/
theorem module_sub_eq_add_neg_one_smul (a b : M) : a - b = a + (-1 : K) • b := by
  rw [neg_one_smul, sub_eq_add_neg]

/-- Negation distributes over addition in a module. -/
theorem module_neg_add (a b : M) : -(a + b) = -a + -b := neg_add a b

/-- Double negation in a module. -/
theorem module_neg_neg (a : M) : -(-a) = a := neg_neg a

end ModuleBasics

/-!
## Section: Module Examples

Any commutative ring K is a module over itself.
-/

section ModuleExamples

-- Any commutative ring is a module over itself
example {K : Type*} [CommRing K] : Module K K := inferInstance

-- ℚ is a module over ℤ
example : Module ℤ ℚ := inferInstance

-- ℝ is a module over ℚ (noncomputable due to real number representation)
noncomputable example : Module ℚ ℝ := inferInstance

-- ℂ is a module over ℝ (noncomputable)
noncomputable example : Module ℝ ℂ := inferInstance

end ModuleExamples

/-!
## Section: Finite Sums and Products

The source emphasizes that finite sums and products in commutative rings are well-defined
regardless of the order of operations or placement of parentheses.

In Mathlib, this is captured by `Finset.sum` and `Finset.prod`.
-/

section FiniteSumsProducts

variable {K : Type*} [CommRing K]
variable {S : Type*}

/-- Finite sums can be split over disjoint sets. -/
theorem sum_disjoint_union [DecidableEq S] {X Y : Finset S} (hXY : Disjoint X Y) (f : S → K) :
    ∑ s ∈ X ∪ Y, f s = ∑ s ∈ X, f s + ∑ s ∈ Y, f s :=
  Finset.sum_union hXY

/-- Finite sums distribute over addition. -/
theorem sum_add_distrib' {T : Finset S} (f g : S → K) :
    ∑ s ∈ T, (f s + g s) = ∑ s ∈ T, f s + ∑ s ∈ T, g s :=
  Finset.sum_add_distrib

/-- Empty sum equals zero. -/
theorem sum_empty (f : S → K) : ∑ _s ∈ (∅ : Finset S), f _s = 0 :=
  Finset.sum_empty

/-- Empty product equals one. -/
theorem prod_empty (f : S → K) : ∏ _s ∈ (∅ : Finset S), f _s = 1 :=
  Finset.prod_empty

end FiniteSumsProducts

/-!
## Section: Inverses in Commutative Rings (def.commring.inverse)

**Definition (def.commring.inverse)**: Let `L` be a commutative ring. Let `a ∈ L`. Then:

- **(a)** An **inverse** (or **multiplicative inverse**) of `a` means an element `b ∈ L`
  such that `a * b = b * a = 1` (where `1` is the unity of `L`).

- **(b)** We say that `a` is **invertible** in `L` (or a **unit** of `L`) if `a` has an inverse.

**Note**: The condition `a * b = b * a = 1` in part (a) can be restated as simply `a * b = 1`,
because we automatically have `a * b = b * a` (since `L` is a commutative ring). The source
writes `a * b = b * a = 1` so that the definition applies verbatim to noncommutative rings as well.

**Examples**:
- In `ℤ`, the only invertible elements are `1` and `-1`. Each is its own inverse.
- In `ℚ`, `ℝ`, `ℂ` (and any field), every nonzero element is invertible.

In Mathlib, this is captured by:
- `IsUnit a` : the predicate that `a` is invertible (a unit)
- `Lˣ` (or `Units L`) : the type of units of `L`, which forms a group under multiplication
- For `u : Lˣ`, we have `u⁻¹ : Lˣ` (the inverse unit)
-/

section InverseDefinition

variable {L : Type*} [CommRing L]

/-!
### Definition def.commring.inverse (a): Inverse of an element

An **inverse** of `a` is an element `b` such that `a * b = 1` (and equivalently `b * a = 1`
in a commutative ring).
-/

/-- **Definition def.commring.inverse (a)**: `b` is an inverse of `a` if `a * b = 1`.
    In a commutative ring, this is equivalent to `b * a = 1`. -/
def IsInverse (a b : L) : Prop := a * b = 1

/-- In a commutative ring, `IsInverse a b` is symmetric: if `a * b = 1`, then `b * a = 1`. -/
theorem isInverse_comm (a b : L) : IsInverse a b ↔ IsInverse b a := by
  simp only [IsInverse, mul_comm]

/-- The inverse relation is symmetric in commutative rings. -/
theorem isInverse_symm {a b : L} (h : IsInverse a b) : IsInverse b a := by
  rwa [isInverse_comm]

/-- `1` is an inverse of `1`. -/
theorem isInverse_one_one : IsInverse (1 : L) 1 := by simp [IsInverse]

/-- `0` has no inverse (unless `L` is the trivial ring where `0 = 1`). -/
theorem not_isInverse_zero_of_nontrivial [Nontrivial L] (b : L) : ¬IsInverse (0 : L) b := by
  simp [IsInverse]

/-! RepoProver post-hoc semantic coverage check.
The aligned gold statement below is grader-only and was not shown to generation. -/

-- Generated declaration(s) under the original target file prefix context.
theorem inverse_unique {L : Type _} [CommRing L] (a b c : L) (h1 : a * b = 1) (h2 : b * a = 1) (h3 : a * c = 1) (h4 : c * a = 1) : b = c :=
by
  calc
    b = b * 1 := by simpa using (mul_one b).symm
    _ = b * (a * c) := by rw [h3]
    _ = (b * a) * c := by rw [mul_assoc]
    _ = 1 * c := by rw [h2]
    _ = c := by simpa using one_mul c

-- Grader-only check: original aligned statement proved from generated theorem(s).
/-- If `a` has an inverse, then `a * b = 1` implies `b` is that inverse.
    Label: thm.commring.inverse-uni -/
theorem __repoprover_latex_statement_check {a b c : L} (hab : IsInverse a b) (hac : IsInverse a c) : b = c := by
  first
  | simpa using inverse_unique a b c h1 h2 h3 h4
  | simpa using inverse_unique L a b c h1 h2 h3 h4
  | simpa using inverse_unique
  | simpa using inverse_unique hab hac
  | simpa using inverse_unique a b c hab hac
