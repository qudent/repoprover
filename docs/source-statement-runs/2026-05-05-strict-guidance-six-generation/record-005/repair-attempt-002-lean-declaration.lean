theorem perm_pow_succ (α : Equiv.Perm X) (n : ℕ) : α ^ (n + 1) = α ^ n * α := by
  exact pow_succ α n
