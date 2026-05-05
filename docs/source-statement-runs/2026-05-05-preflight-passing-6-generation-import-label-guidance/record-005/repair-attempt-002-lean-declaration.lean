lemma coeff_X_eq (n : ℕ) : coeff n (X : R⟦X⟧) = if n = 1 then 1 else 0 := by
  simp [X, coeff_mk]
