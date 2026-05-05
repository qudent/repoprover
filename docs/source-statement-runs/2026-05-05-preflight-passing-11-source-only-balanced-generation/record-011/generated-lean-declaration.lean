/-- Simple transposition `s_i` equals the transposition `t_{i,i+1}`. (def.perm.si) -/
theorem simpleTransposition_eq_transposition {n : ℕ} (i : Fin (n - 1)) :
    simpleTransposition i = transposition
      ⟨i.val, Nat.lt_of_lt_of_le i.isLt (Nat.sub_le n 1)⟩
      ⟨i.val + 1, by omega⟩ := rfl
