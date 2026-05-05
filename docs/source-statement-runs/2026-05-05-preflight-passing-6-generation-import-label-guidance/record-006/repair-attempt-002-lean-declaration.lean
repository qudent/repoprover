theorem partsCount_eq_largestPart_count (k n : ℕ) : partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun p => largestPart p = k)).card := by
  have hinj : Function.Injective (Nat.Partition.transpose (n := n)) := by
    intro p q h
    apply_fun (fun p : Partition n => p.transpose) at h
    simpa [transpose_transpose] using h
  have hcard_image : (Finset.image (Nat.Partition.transpose (n := n))
      (Finset.filter (fun p => numParts p = k) Finset.univ)).card =
    (Finset.filter (fun p => numParts p = k) Finset.univ).card :=
    Finset.card_image_of_injective _ hinj
  have himage_eq : Finset.image (Nat.Partition.transpose (n := n))
      (Finset.filter (fun p => numParts p = k) Finset.univ) =
    (Finset.univ : Finset (Partition n)).filter (fun p => largestPart p = k) := by
    ext q
    constructor
    · intro h
      rcases Finset.mem_image.1 h with ⟨p, hp, rfl⟩
      simp [Finset.mem_filter, hp, transpose_largestPart_eq_length]
    · intro h
      rcases Finset.mem_filter.1 h with ⟨hq_univ, hq_larg⟩
      have hq_trans_num : numParts (q.transpose) = k := by
        rw [transpose_length_eq_largestPart q, hq_larg]
      apply Finset.mem_image.mpr
      exact ⟨q.transpose, by
        simp [hq_trans_num, Finset.mem_filter, Finset.mem_univ],
        by rw [transpose_transpose]⟩
  calc
    partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun p => Multiset.card p.parts = k)).card := rfl
    _ = ((Finset.univ : Finset (Partition n)).filter (fun p => numParts p = k)).card := by
      congr; ext p; simp [numParts]
    _ = (Finset.image (Nat.Partition.transpose (n := n))
          (Finset.filter (fun p => numParts p = k) Finset.univ)).card := by rw [hcard_image]
    _ = ((Finset.univ : Finset (Partition n)).filter (fun p => largestPart p = k)).card := by rw [himage_eq]
