theorem fps_comp_coeff_finite (f g : K⟦X⟧) (hg : constantCoeff g = 0) (n : ℕ) :
    coeff n (PowerSeries.subst g f) = (Finset.range (n+1)).sum (fun d => coeff d f * coeff n (g ^ d)) := by
  rw [fps_comp_coeff f g hg n]
  apply finsum_eq_sum_of_support_subset
  intro d hd
  have hzero : coeff n (g ^ d) = 0 := by
    have h_lt : n < d := by
      simpa [Finset.mem_range] using hd
    exact fps_subs_wd_firstCoeffs g hg d n h_lt
  simp [hzero]
