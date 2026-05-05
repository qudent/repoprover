theorem fps_subst_eq_tsum (f g : K⟦X⟧) (hg : constantCoeff g = 0) : PowerSeries.subst g f = ∑' n : ℕ, coeff n f • g ^ n := by
  have hsum : Summable (fun (n : ℕ) => coeff n f • g ^ n) := by
    rw [summable_power_series]
    intro k
    apply Filter.eventually_atTop.mpr
    use k + 1
    intro n hn
    have hk : k < n := by omega
    simp [coeff_smul, fps_subs_wd_firstCoeffs g hg n k hk]
  ext n
  rw [fps_comp_coeff f g hg n, coeff_tsum hsum]
  have hzero : ∀ d, d ∉ Finset.range (n + 1) → coeff d f * coeff n (g ^ d) = 0 := by
    intro d hd
    have hdn : n < d := by
      by_contra! hle
      apply hd
      apply Finset.mem_range.mpr
      omega
    simp [fps_subs_wd_firstCoeffs g hg d n hdn]
  rw [tsum_eq_sum (s := Finset.range (n+1)) (h := hzero)]
  have hsupport : (fun d : ℕ => coeff d f * coeff n (g ^ d)) support ⊆ (Finset.range (n+1) : Set ℕ) := by
    intro d hd
    simp at hd
    by_cases hdn : n < d
    · exfalso
      apply hd
      simp [fps_subs_wd_firstCoeffs g hg d n hdn]
    · apply Finset.mem_coe.mpr
      apply Finset.mem_range.mpr
      omega
  rw [finsum_eq_sum_of_support_subset _ hsupport]
