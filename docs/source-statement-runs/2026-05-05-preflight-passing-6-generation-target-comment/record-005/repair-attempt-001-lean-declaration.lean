lemma coeff_X_eq (n : ℕ) : coeff n (X : R⟦X⟧) = if n = 1 then (1 : R) else 0 := by
  simpa using coeff_X n
