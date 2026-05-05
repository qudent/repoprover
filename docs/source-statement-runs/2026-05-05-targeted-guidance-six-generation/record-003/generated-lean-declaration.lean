lemma fps_comp_coeff_finsum_eq_sum (f g : K⟦X⟧) (hg : constantCoeff g = 0) (n : ℕ) :
    finsum (fun d ↦ coeff d f * coeff n (g ^ d)) = ∑ d in Finset.range (n + 1), coeff d f * coeff n (g ^ d) :=
by
  apply finsum_eq_sum_of_support_subset
  intro d hd
  have hmem : d ∉ Finset.range (n + 1) := hd
  rw [Finset.mem_range] at hmem
  have hnd : n < d := by omega
  have hzero : coeff n (g ^ d) = 0 := fps_subs_wd_firstCoeffs g hg d n hnd
  simpa
