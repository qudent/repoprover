/-- Swapping two entries of α negates the alternant. (lem.sf.alternant-0 (b)) -/
theorem alternant_swap_of_ne {α : Fin N → ℕ} {i j : Fin N} (hij : i ≠ j) :
    alternant (R := R) N (α ∘ Equiv.swap i j) = - alternant N α :=
  AlgebraicCombinatorics.alternant_swap (R := R) hij
