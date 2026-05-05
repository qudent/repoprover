theorem fps_newton_binom (F : Type*) [Field F] [BinomialRing F] (n : ℕ) : ((1 + PowerSeries.X : PowerSeries F)⁻¹) ^ n = PowerSeries.mk fun k => (Ring.choose (-(n : ℤ)) k : F) :=
  fps_onePlusX_pow_neg' F n
