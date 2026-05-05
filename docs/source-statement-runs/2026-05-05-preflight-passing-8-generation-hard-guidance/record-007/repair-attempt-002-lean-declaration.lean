theorem simpleTransposition_apply_of_ne_of_ne {n : ℕ} (i : Fin (n - 1)) (k : Fin n) (h_val1 : k.val ≠ i.val) (h_val2 : k.val ≠ i.val + 1) : simpleTransposition i k = k := by
  have hk1 : k ≠ ⟨i.val, Nat.lt_of_lt_of_le i.isLt (Nat.sub_le n 1)⟩ := by
    intro h
    apply h_val1
    simpa using congr_arg Fin.val h
  have hk2 : k ≠ ⟨i.val + 1, by omega⟩ := by
    intro h
    apply h_val2
    simpa using congr_arg Fin.val h
  unfold simpleTransposition
  exact Equiv.swap_apply_of_ne_of_ne hk1 hk2
