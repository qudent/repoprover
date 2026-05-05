/-- Simple transposition `s_i` is a swap. (def.perm.si) -/
theorem simpleTransposition_isSwap {n : ℕ} (i : Fin (n - 1)) : (simpleTransposition i).IsSwap := by
  have h_ne : (⟨i.val, Nat.lt_of_lt_of_le i.isLt (Nat.sub_le n 1)⟩ : Fin n) ≠ ⟨i.val+1, by omega⟩ := by
    intro h
    have hval : (⟨i.val, Nat.lt_of_lt_of_le i.isLt (Nat.sub_le n 1)⟩ : Fin n).val = (⟨i.val+1, by omega⟩ : Fin n).val := congrArg Fin.val h
    have : i.val = i.val + 1 := by simpa using hval
    exact (Nat.succ_ne_self i.val) this
  refine ⟨⟨i.val, Nat.lt_of_lt_of_le i.isLt (Nat.sub_le n 1)⟩, ⟨i.val+1, by omega⟩, h_ne, ?_⟩
  rfl
