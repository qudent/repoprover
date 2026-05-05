theorem empty_partition_unique (p : Nat.Partition 0) : p = empty := by
  have hsum : p.entries.sum = 0 := p.sum_eq
  have hnull : p.entries = [] := by
    by_contra hne
    have hzero : ∀ a ∈ p.entries, a = 0 :=
      List.sum_eq_zero_iff.mp hsum
    have hpos : ∀ a ∈ p.entries, 0 < a := p.pos
    obtain ⟨a, ha⟩ := List.exists_mem_of_ne_nil hne
    have hz := hzero a ha
    have hp := hpos a ha
    exact (lt_irrefl 0) (hz ▸ hp)
  apply Nat.Partition.ext
  exact hnull
