theorem fps_newton_binom {F : Type*} [Field F] [BinomialRing F] (n : ℕ) :
    ((1 + PowerSeries.X : PowerSeries F) ^ n)⁻¹ = PowerSeries.mk (λ k => (Ring.choose (-(n : ℤ)) k : F)) := by
  have hc : PowerSeries.constantCoeff (1 + PowerSeries.X : PowerSeries F) ≠ 0 := by simp
  have h_inv2 : ((1 + PowerSeries.X : PowerSeries F)⁻¹) ^ n * ((1 + PowerSeries.X : PowerSeries F) ^ n) = 1 := by
    calc
      ((1 + PowerSeries.X : PowerSeries F)⁻¹) ^ n * ((1 + PowerSeries.X : PowerSeries F) ^ n) = (((1 + PowerSeries.X : PowerSeries F)⁻¹) * (1 + PowerSeries.X : PowerSeries F)) ^ n := by rw [mul_pow]
      _ = 1 ^ n := by rw [PowerSeries.inv_mul_cancel (1 + PowerSeries.X : PowerSeries F) hc]
      _ = 1 := by simp
  have hc_n : PowerSeries.constantCoeff ((1 + PowerSeries.X : PowerSeries F) ^ n) ≠ 0 := by
    simpa [PowerSeries.constantCoeff_pow] using pow_ne_zero n hc
  have h_inv_pow : ((1 + PowerSeries.X : PowerSeries F)⁻¹) ^ n = ((1 + PowerSeries.X : PowerSeries F) ^ n)⁻¹ := by
    symm
    apply (PowerSeries.inv_eq_iff_mul_eq_one hc_n).mpr h_inv2
  calc
    ((1 + PowerSeries.X : PowerSeries F) ^ n)⁻¹ = ((1 + PowerSeries.X : PowerSeries F)⁻¹) ^ n := by rw [h_inv_pow.symm]
    _ = PowerSeries.mk (λ k => (Ring.choose (-(n : ℤ)) k : F)) := by rw [fps_onePlusX_pow_neg' n]
