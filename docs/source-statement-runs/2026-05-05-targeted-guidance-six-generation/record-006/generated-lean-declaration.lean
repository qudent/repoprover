theorem simpleTransposition_isSwap {n : ℕ} (i : Fin (n - 1)) : (simpleTransposition i).IsSwap := by
  unfold simpleTransposition
  have hne : (⟨i.val, Nat.lt_of_lt_of_le i.isLt (Nat.sub_le n 1)⟩ : Fin n) ≠
            (⟨i.val + 1, by omega⟩ : Fin n) := by
    intro h
    apply_fun (fun x => x.val) at h
    omega
  apply Equiv.swap_isSwap
  exact hne
