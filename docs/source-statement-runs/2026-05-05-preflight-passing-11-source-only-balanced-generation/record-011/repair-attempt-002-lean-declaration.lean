/-- Simple transposition `s_i` is a swap. (def.perm.si) -/
theorem simpleTransposition_isSwap {n : ℕ} (i : Fin (n - 1)) : (simpleTransposition i).IsSwap := by
  let a : Fin n := ⟨i.val, Nat.lt_of_lt_of_le i.isLt (Nat.sub_le n 1)⟩
  let b : Fin n := ⟨i.val + 1, by omega⟩
  have ha_ne_b : a ≠ b := by
    intro h
    have hval : a.val = b.val := congrArg Fin.val h
    omega
  refine ⟨a, b, ha_ne_b, ?_⟩
  rfl
