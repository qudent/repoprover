lemma x_coeff_spec : coeff 1 (X : R⟦X⟧) = 1 ∧ ∀ i : ℕ, i ≠ 1 → coeff i (X : R⟦X⟧) = 0 := by
  constructor
  · simp
  · intro i hi
    simp [hi]
