theorem sum_lim_conv (f : ℕ → PowerSeries K) (L : PowerSeries K) (h : CoeffStabilizesTo (fun i => ∑ j ∈ Finset.range (i+1), f j) L) : IsSummable f ∧ tsum' f (show IsSummable f from ⟨L, h⟩) = L :=
by
  have hsum : IsSummable f := ⟨L, h⟩
  have h_tsum_eq : tsum' f hsum = L := by
    have h_tsum_limit : CoeffStabilizesTo (fun i => ∑ j ∈ Finset.range (i+1), f j) (tsum' f hsum) :=
      coeffStabilizesTo_partial_sum' hsum
    have h_unique : ∀ (L' : PowerSeries K), CoeffStabilizesTo (fun i => ∑ j ∈ Finset.range (i+1), f j) L' → L' = L := by
      intro L' hL'
      apply coeff_inj
      intro n
      obtain ⟨N, hN⟩ := h n
      obtain ⟨N', hN'⟩ := hL' n
      let Nmax := max N N'
      have hNmax : ∀ i ≥ Nmax, xnEquiv n (∑ j ∈ Finset.range (i+1), f j) L := by
        intro i hi
        apply hN i (le_of_max_le_left hi)
      have hNmax' : ∀ i ≥ Nmax, xnEquiv n (∑ j ∈ Finset.range (i+1), f j) L' := by
        intro i hi
        apply hN' i (le_of_max_le_right hi)
      have hxnL := hNmax Nmax (le_refl Nmax)
      have hxnL' := hNmax' Nmax (le_refl Nmax)
      have hcoeffL := hxnL n (le_refl n)
      have hcoeffL' := hxnL' n (le_refl n)
      rw [← hcoeffL, hcoeffL']
    exact h_unique (tsum' f hsum) h_tsum_limit
  exact ⟨hsum, h_tsum_eq⟩
