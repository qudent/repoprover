theorem fps_comp_coeff_eq_finset_sum (f g : K⟦X⟧) (hg : constantCoeff g = 0) (n : ℕ) :
    coeff n (PowerSeries.subst g f) = Finset.sum (Finset.range (n+1)) (fun d => coeff d f * coeff n (g ^ d)) := by
  rw [fps_comp_coeff f g hg n]
  have hzero : ∀ (d : ℕ), d ∉ Finset.range (n+1) → coeff d f * coeff n (g ^ d) = 0 := by
    intro d hd
    rw [Finset.mem_range] at hd
    have hn_succ_le_d : n+1 ≤ d := Nat.ge_of_not_lt hd
    have h_lt : n < d := Nat.lt_of_succ_le hn_succ_le_d
    have hcoeff : coeff n (g ^ d) = 0 := fps_subs_wd_firstCoeffs g hg d n h_lt
    rw [hcoeff, mul_zero]
  exact finsum_eq_sum_finset hzero
