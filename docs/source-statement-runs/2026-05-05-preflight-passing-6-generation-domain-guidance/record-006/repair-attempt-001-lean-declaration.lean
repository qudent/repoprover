theorem partsCount_eq_number_of_partitions_with_largestPart (n k : ℕ) : partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun p => p.largestPart = k)).card := by
  have h_transpose_involutive : Function.Involutive (fun (p : Partition n) => p.transpose) := by
    intro p; exact transpose_transpose p
  have h_transpose_injective : Function.Injective (fun (p : Partition n) => p.transpose) :=
    h_transpose_involutive.injective
  set A := (Finset.univ : Finset (Partition n)).filter (fun p => p.numParts = k) with hA
  set B := (Finset.univ : Finset (Partition n)).filter (fun p => p.largestPart = k) with hB
  have h_sub1 : A.image (fun p : Partition n => p.transpose) ⊆ B := by
    intro p hp
    rcases Finset.mem_image.1 hp with ⟨q, hq, rfl⟩
    rw [hB, Finset.mem_filter]
    refine ⟨Finset.mem_univ _, ?_⟩
    rw [hA, Finset.mem_filter] at hq
    rcases hq with ⟨_, hq_numParts⟩
    rw [transpose_largestPart_eq_length q, hq_numParts]
  have h_sub2 : B ⊆ A.image (fun p : Partition n => p.transpose) := by
    intro p hp
    rw [hB, Finset.mem_filter] at hp
    rcases hp with ⟨_, hp_largestPart⟩
    have h_num : (p.transpose).numParts = k := by
      rw [transpose_length_eq_largestPart p, hp_largestPart]
    have hA_mem : p.transpose ∈ A := by
      rw [hA, Finset.mem_filter]
      refine ⟨Finset.mem_univ _, h_num⟩
    refine Finset.mem_image.mpr ⟨p.transpose, hA_mem, ?_⟩
    simpa using transpose_transpose p
  have h_image_A_eq_B : A.image (fun p : Partition n => p.transpose) = B :=
    Finset.Subset.antisymm h_sub1 h_sub2
  have hcard : (A.image (fun p : Partition n => p.transpose)).card = A.card :=
    Finset.card_image_of_injective A h_transpose_injective
  calc
    partsCount k n = A.card := by
      unfold partsCount
      rw [hA]
      simp [numParts]
    _ = (A.image (fun p : Partition n => p.transpose)).card := by rw [← hcard]
    _ = B.card := by rw [h_image_A_eq_B]
    _ = ((Finset.univ : Finset (Partition n)).filter (fun p => p.largestPart = k)).card := by rw [hB]
