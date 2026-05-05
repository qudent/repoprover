theorem lexLt_irrefl {n : ℕ} (a : Fin n → ℤ) : ¬ lexLt a a := by
  intro h
  rcases h with ⟨k, _, hlt⟩
  exact lt_irrefl (a k) hlt
