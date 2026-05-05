theorem size_eq_zero_iff_eq_empty (p : Nat.Partition) : p.size = 0 ↔ p = empty := by
  constructor
  · intro h
    have hsum : p.entries.sum = 0 := by
      simpa [size] using h
    have hnull : p.entries = [] := by
      by_contra hne
      have hpos_sum : 0 < p.entries.sum := List.sum_pos p.pos hne
      linarom
    apply Nat.Partition.ext
    exact hnull
  · intro h
    rw [h]
    simp [size, empty]
