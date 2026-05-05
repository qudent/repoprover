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
      rw [Finset.mem_filter]
      have hqA : Multiset.card q.parts = k := by
        simpa [A, Finset.mem_filter] using hq
      have hlargest : q.transpose.largestPart = k := by
        calc
          q.transpose.largestPart = q.numParts := transpose_largestPart_eq_length q
          _ = Multiset.card q.parts := rfl
          _ = k := hqA
      exact ⟨Finset.mem_univ _, hlargest⟩
    · intro h
      rw [Finset.mem_filter] at h
      rcases h with ⟨h_univ, h_largest⟩
      have h_card_transpose : Multiset.card (p.transpose.parts) = k := by
        calc
          Multiset.card (p.transpose.parts) = p.transpose.numParts := rfl
          _ = p.largestPart := transpose_length_eq_largestPart p
          _ = k := h_largest
      apply Finset.mem_image.mpr
      refine ⟨p.transpose, Finset.mem_filter.mpr ⟨Finset.mem_univ _, h_card_transpose⟩, ?_⟩
      exact transpose_transpose p
  calc
    partsCount k n = A.card := hA
    _ = (Finset.image transpose A).card := by rw [Finset.card_image_of_injective _ h_inj]
    _ = B.card := by rw [h_image_eq]
