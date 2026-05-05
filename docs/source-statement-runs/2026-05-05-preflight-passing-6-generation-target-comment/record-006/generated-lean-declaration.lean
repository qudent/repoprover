lemma partsCount_eq_card_largestPart_eq (k n : ℕ) : partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun p => largestPart p = k)).card := by
  rw [partsCount]
  apply Finset.card_congr (fun p _ => p.transpose)
  · intro p hp
    rw [Finset.mem_filter] at hp
    rcases hp with ⟨hp_univ, hp_numParts⟩
    refine ⟨Finset.mem_univ _, ?_⟩
    rw [transpose_largestPart_eq_length, hp_numParts]
  · intro p1 hp1 p2 hp2 h_eq
    calc
      p1 = p1.transpose.transpose := by rw [transpose_transpose]
      _ = p2.transpose.transpose := by rw [h_eq]
      _ = p2 := by rw [transpose_transpose]
  · intro q hq
    rw [Finset.mem_filter] at hq
    rcases hq with ⟨hq_univ, hq_largestPart⟩
    refine ⟨q.transpose, ?_, ?_⟩
    · rw [Finset.mem_filter]
      refine ⟨Finset.mem_univ _, ?_⟩
      rw [transpose_length_eq_largestPart, hq_largestPart]
    · rw [transpose_transpose]
