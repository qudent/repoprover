theorem simpleTransposition_apply_of_ne_of_ne {n : ℕ} (i : Fin (n - 1)) (k : Fin n) (h1 : k ≠ ⟨i.val, Nat.lt_of_lt_of_le i.isLt (Nat.sub_le n 1)⟩) (h2 : k ≠ ⟨i.val + 1, by omega⟩) : simpleTransposition i k = k :=
  by
    unfold simpleTransposition
    exact Equiv.swap_apply_of_ne_of_ne h1 h2
