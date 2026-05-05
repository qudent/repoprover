lemma partsCount_eq_card_largestPart_eq (k n : ℕ) : partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun (p : Partition n) => largestPart p = k)).card := by
  have hinj : Function.Injective (transpose : Partition n → Partition n) := by
    intro p q h
    calc
      p = p.transpose.transpose := by rw [transpose_transpose]
      _ = q.transpose.transpose := by rw [h]
      _ = q := by rw [transpose_transpose]
  have h_image : (Finset.univ.filter (fun (p : Partition n) => Multiset.card p.parts = k)).image (transpose : Partition n → Partition n) = 
      Finset.univ.filter (fun (p : Partition n) => largestPart p = k) := by
    ext p
    constructor
    · intro hp
      rcases Finset.mem_image.1 hp with ⟨q, hq, rfl⟩
      rw [Finset.mem_filter] at hq
      rcases hq with ⟨hq_univ, hq_card⟩
      refine Finset.mem_filter.mpr ⟨Finset.mem_univ _, ?_⟩
      rw [transpose_largestPart_eq_length, numParts, hq_card]
    · intro hp
      rw [Finset.mem_filter] at hp
      rcases hp with ⟨hp_univ, hp_largestPart⟩
      have hq : p.transpose ∈ Finset.univ.filter (fun (p : Partition n) => Multiset.card p.parts = k) := by
        apply Finset.mem_filter.mpr
        refine ⟨Finset.mem_univ _, ?_⟩
        rw [← numParts, transpose_length_eq_largestPart, hp_largestPart]
      refine Finset.mem_image.mpr ⟨p.transpose, hq, ?_⟩
      rw [transpose_transpose]
  calc
    partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun (p : Partition n) => Multiset.card p.parts = k)).card := by rw [partsCount]
    _ = ((Finset.univ.filter (fun (p : Partition n) => Multiset.card p.parts = k)).image (transpose : Partition n → Partition n)).card := by
      rw [Finset.card_image_of_injective _ hinj]
    _ = ((Finset.univ : Finset (Partition n)).filter (fun (p : Partition n) => largestPart p = k)).card := by rw [h_image]
