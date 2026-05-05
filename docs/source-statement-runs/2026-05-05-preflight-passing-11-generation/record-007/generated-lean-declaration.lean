/-- Alternative coefficient formula for the composition of formal power series (Definition 7.3.1).
For any fixed n, the sum ∑_{d∈ℕ} fₐ · [xⁿ](g^d) is actually finite, since [xⁿ](g^d) = 0 for d > n when g has constant term 0.
This gives a finite sum representation of the coefficient. -/
theorem fps_comp_coeff_eq_finset_sum (f g : K⟦X⟧) (hg : constantCoeff g = 0) (n : ℕ) :
    coeff n (PowerSeries.subst g f) = ∑ d in Finset.range (n+1), coeff d f * coeff n (g ^ d) := by
  rw [fps_comp_coeff f g hg n]
  apply finsum_eq_finset_sum (fun d ↦ coeff d f * coeff n (g ^ d)) (Finset.range (n+1))
  intro d hd
  rw [Finset.mem_range, not_lt] at hd
  have h_lt : n < d := by omega
  have hcoeff : coeff n (g ^ d) = 0 := fps_subs_wd_firstCoeffs g hg d n h_lt
  rw [hcoeff, mul_zero]
