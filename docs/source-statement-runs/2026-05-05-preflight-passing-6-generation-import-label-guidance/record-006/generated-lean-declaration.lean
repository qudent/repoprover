theorem partsCount_eq_largestPart_count (k n : ℕ) : partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun p => p.largestPart = k)).card := by
  have hbij : ((Finset.univ.filter (fun p : Partition n => p.numParts = k)).card = (Finset.univ.filter (fun p : Partition n => p.largestPart = k)).card) := by
    apply Finset.card_congr (fun p _ => p.transpose) ?_ ?_ ?_
    · intro p hp
      simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hp
      have hp_num : p.numParts = k := hp
      rw [transpose_largestPart_eq_length, hp_num]
    · intro q hq
      simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hq
      have hq_largest : q.largestPart = k := hq
      use q.transpose
      constructor
      · rw [transpose_length_eq_largestPart, hq_largest]
      · rw [transpose_transpose]
    · intro p1 p2 hp1 hp2 htrans
      simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hp1 hp2
      apply_fun (fun p : Partition n => p.transpose) at htrans
      rw [transpose_transpose, transpose_transpose] at htrans
      exact htrans
  calc
    partsCount k n = ((Finset.univ : Finset (Partition n)).filter (fun p => Multiset.card p.parts = k)).card := rfl
    _ = ((Finset.univ : Finset (Partition n)).filter (fun p => p.numParts = k)).card := by
      congr; ext p; simp [numParts]
    _ = ((Finset.univ : Finset (Partition n)).filter (fun p => p.largestPart = k)).card := hbij
