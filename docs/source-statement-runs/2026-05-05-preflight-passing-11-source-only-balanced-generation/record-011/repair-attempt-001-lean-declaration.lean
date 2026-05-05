/-- Simple transposition `s_i` is a swap. (def.perm.si) -/
theorem simpleTransposition_isSwap {n : ℕ} (i : Fin (n - 1)) : (simpleTransposition i).IsSwap := by
  unfold simpleTransposition; exact Equiv.swap_isSwap _ _
