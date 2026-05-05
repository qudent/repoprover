theorem sum_lim_conv {f : ℕ → PowerSeries K} {L : PowerSeries K}
    (h : CoeffStabilizesTo (fun i => ∑ j ∈ Finset.range (i + 1), f j) L) :
    ∃ (hsum : IsSummable f), tsum' f hsum = L :=
by
  have hsum : IsSummable f := by
    intro n
    rcases h n with ⟨N, hN⟩
    have hzero : ∀ i, N ≤ i → coeff n (f (i+1)) = 0 := by
      intro i hi
      have hsum_i1 : coeff n (∑ j ∈ Finset.range (i+1+1), f j) = coeff n L := hN (i+1) (by omega)
      have hsum_i : coeff n (∑ j ∈ Finset.range (i+1), f j) = coeff n L := hN i hi
      have hsum_eq : coeff n (∑ j ∈ Finset.range (i+1+1), f j) = coeff n (∑ j ∈ Finset.range (i+1), f j) + coeff n (f (i+1)) := by
        calc
          coeff n (∑ j ∈ Finset.range (i+1+1), f j) = ∑ j ∈ Finset.range (i+1+1), coeff n (f j) := coeff_sum _ _ _
          _ = (∑ j ∈ Finset.range (i+1), coeff n (f j)) + coeff n (f (i+1)) := by simp [Finset.sum_range_succ]
          _ = coeff n (∑ j ∈ Finset.range (i+1), f j) + coeff n (f (i+1)) := by simp [coeff_sum]
      rw [hsum_i1, hsum_i] at hsum_eq
      linarith
    have hsubset : {i | coeff n (f i) ≠ 0} ⊆ Finset.range (N+1) := by
      intro i hi
      simp at hi
      have hi_le_N : i ≤ N := by
        by_contra! hgt
        apply hi
        rcases Nat.exists_eq_succ_of_ne_zero (by omega : i ≠ 0) with ⟨j, hj⟩
        have hj_ge_N : N ≤ j := by omega
        rw [hj]
        exact hzero j hj_ge_N
      exact Finset.mem_range.mpr hi_le_N
    exact Set.Finite.subset (Finset.finite_toSet (Finset.range (N+1))) hsubset
  have htsum_eq : tsum' f hsum = L := by
    have hpart : CoeffStabilizesTo (fun i => ∑ j ∈ Finset.range (i+1), f j) (tsum' f hsum) :=
      coeffStabilizesTo_partial_sum' hsum
    apply PowerSeries.ext
    intro n
    rcases hpart n with ⟨N1, hN1⟩
    rcases h n with ⟨N2, hN2⟩
    let N := max N1 N2
    have hcoeff_eq : coeff n (tsum' f hsum) = coeff n L := by
      calc
        coeff n (tsum' f hsum) = coeff n ((fun i => ∑ j ∈ Finset.range (i+1), f j) N) := by
          symm; apply hN1 N (le_max_left _ _)
        _ = coeff n L := hN2 N (le_max_right _ _)
    exact hcoeff_eq
  exact ⟨hsum, htsum_eq⟩
