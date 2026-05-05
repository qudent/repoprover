theorem perm_pow_apply_eq_iterate (α : Equiv.Perm X) (n : ℕ) (x : X) : (α ^ n) x = (α ^[n]) x := by
  rw [Equiv.Perm.coe_pow]
