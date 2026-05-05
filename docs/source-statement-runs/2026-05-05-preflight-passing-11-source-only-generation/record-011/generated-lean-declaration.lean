theorem simpleTransposition_sq_eq_one {n : ℕ} (i : Fin (n - 1)) : simpleTransposition i * simpleTransposition i = 1 := by
  simp [simpleTransposition, Equiv.swap_mul_self]
