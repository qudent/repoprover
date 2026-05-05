theorem partsCount_eq_card_largestPart (k n : ℕ) : partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun p => p.largestPart = k)).card :=
by
  let A := (Finset.univ : Finset (Partition n)).filter (fun p => Multiset.card p.parts = k)
  let B := (Finset.univ : Finset (Partition n)).filter (fun p => p.largestPart = k)
  have hA : partsCount k n = A.card := rfl
  have h_inj : Function.Injective (transpose : Partition n → Partition n) := by
    intro p q h
    apply_fun transpose at h
    simpa [transpose_transpose] using h
  have h_image_eq : Finset.image transpose A = B := by
    ext p
    constructor
    · intro h
      rcases Finset.mem_image.mp h with ⟨q, hq, rfl⟩
      rw [Finset.mem_filter, Finset.mem_univ, true_and]
      rw [Finset.mem_filter] at hq
      rw [transpose_largestPart_eq_length q]
      exact hq.2
    · intro h
      rw [Finset.mem_filter] at h
      have hp_largest : p.largestPart = k := h.2
      apply Finset.mem_image.mpr
      refine ⟨p.transpose, Finset.mem_filter.mpr ⟨Finset.mem_univ _, ?_⟩, ?_⟩
      · rw [transpose_length_eq_largestPart p, hp_largest]
      · exact (transpose_transpose p).symm
  calc
    partsCount k n = A.card := hA
    _ = (Finset.image transpose A).card := by rw [Finset.card_image_of_injective _ h_inj]
    _ = B.card := by rw [h_image_eq]
