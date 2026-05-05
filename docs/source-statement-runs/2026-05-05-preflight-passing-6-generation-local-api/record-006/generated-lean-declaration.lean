theorem partsCount_eq_card_largestPart (k n : ℕ) : partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun p => p.largestPart = k)).card :=
by
  apply Finset.card_congr (fun p _ => p.transpose)
  · intro p hp
    rw [Finset.mem_filter] at hp
    refine Finset.mem_filter.mpr ⟨Finset.mem_univ _, ?_⟩
    rw [transpose_largestPart_eq_length p, hp.2]
  · intro q hq
    rw [Finset.mem_filter] at hq
    refine ⟨q.transpose, Finset.mem_filter.mpr ⟨Finset.mem_univ _, ?_⟩, ?_⟩
    · rw [transpose_length_eq_largestPart q, hq.2]
    · exact transpose_transpose q
  · intro p₁ p₂ hp₁ hp₂ h
    rw [Finset.mem_filter] at hp₁ hp₂
    have h' : p₁.transpose.transpose = p₂.transpose.transpose := by rw [h]
    rw [transpose_transpose p₁, transpose_transpose p₂] at h'
    exact h'
