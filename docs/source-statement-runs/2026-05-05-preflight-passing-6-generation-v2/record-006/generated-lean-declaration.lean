lemma partsCount_eq_largestPart_count (k n : ℕ) : partsCount k n =
    ((Finset.univ : Finset (Partition n)).filter (fun p => p.largestPart = k)).card := by
  apply Finset.card_congr (fun p _ => p.transpose) ?_ ?_ ?_ ?_
  · intro p hp
    rw [Finset.mem_filter, Finset.mem_univ, true_and] at hp ⊢
    have hp_eq : p.numParts = k := by
      rw [numParts]
      exact hp
    rw [transpose_largestPart_eq_length, hp_eq]
  · intro p₁ hp₁ p₂ hp₂ htrans_eq
    calc
      p₁ = p₁.transpose.transpose := by rw [transpose_transpose]
      _ = p₂.transpose.transpose := by rw [htrans_eq]
      _ = p₂ := by rw [transpose_transpose]
  · intro q hq
    rw [Finset.mem_filter, Finset.mem_univ, true_and] at hq
    refine ⟨q.transpose, Finset.mem_filter.mpr ⟨Finset.mem_univ _, ?_⟩, ?_⟩
    · rw [transpose_length_eq_largestPart, hq, numParts]
    · rw [transpose_transpose]
