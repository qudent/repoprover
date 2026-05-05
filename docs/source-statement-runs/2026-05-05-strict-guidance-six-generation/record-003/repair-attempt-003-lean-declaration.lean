theorem fps_comp_coeff_finite (f g : K⟦X⟧) (hg : constantCoeff g = 0) (n : ℕ) :
    coeff n (PowerSeries.subst g f) = (Finset.range (n+1)).sum (fun d => coeff d f * coeff n (g ^ d)) := by
  rw [fps_comp_coeff f g hg n]
  apply finsum_eq_sum_of_support_subset
  intro d hd
  dsimp [Function.support] at hd
  have hcnz : coeff n (g ^ d) ≠ 0 := by
    intro hzero
    apply hd
    simp [hzero]
  have h_le : d ≤ n := by
    by_contra! h_gt
    apply hcnz
    exact fps_subs_wd_firstCoeffs g hg d n h_gt
  have hd_lt : d < n+1 := Nat.lt_succ_of_le h_le
  exact Finset.mem_range.2 hd_lt
