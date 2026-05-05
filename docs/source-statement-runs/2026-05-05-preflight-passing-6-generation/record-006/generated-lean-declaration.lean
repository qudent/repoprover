lemma partsCount_eq_card_filter_largestPart (k n : ℕ) : partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun p => largestPart p = k)).card := by
  unfold partsCount numParts
  apply Finset.card_congr (fun p _ => p.transpose)
  · intro p hp
    rw [Finset.mem_filter] at hp ⊢
    obtain ⟨hp_univ, hp_eq⟩ := hp
    refine ⟨hp_univ, ?_⟩
    rw [transpose_largestPart_eq_length p, hp_eq]
  · intro p hp q hq h
    apply_fun fun p => p.transpose at h
    simp [transpose_transpose] at h
    exact h
  · intro q hq
    rw [Finset.mem_filter] at hq
    obtain ⟨hq_univ, hq_eq⟩ := hq
    use q.transpose
    constructor
    · rw [Finset.mem_filter]
      refine ⟨Finset.mem_univ _, ?_⟩
      rw [transpose_length_eq_largestPart q, hq_eq]
    · rw [transpose_transpose]
