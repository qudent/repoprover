theorem simpleTransposition_isSwap {n : ℕ} (i : Fin (n - 1)) : (simpleTransposition i).IsSwap := by
  have hne : (⟨i.val, Nat.lt_of_lt_of_le i.isLt (Nat.sub_le n 1)⟩ : Fin n) ≠ ⟨i.val + 1, by omega⟩ := by
    intro h
    have hval : i.val = i.val + 1 := congr_arg Fin.val h
    exact Nat.succ_ne_self i.val (Eq.symm hval)
  refine ⟨⟨i.val, Nat.lt_of_lt_of_le i.isLt (Nat.sub_le n 1)⟩, ⟨i.val + 1, by omega⟩, hne, ?_⟩
  rfl
