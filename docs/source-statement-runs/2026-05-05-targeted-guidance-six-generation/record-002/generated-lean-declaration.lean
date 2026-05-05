theorem newton_binom (F : Type*) [Field F] [BinomialRing F] (n : ℤ) : ((1 : PowerSeries F) + PowerSeries.X) ^ (n : ℤ) = PowerSeries.mk fun k => (Ring.choose n k : F) := by
  match n with
  | (m : ℕ) =>
    have h_binom : PowerSeries.binomialSeries F (m : ℤ) = (1 + PowerSeries.X : PowerSeries F) ^ m :=
      PowerSeries.binomialSeries_nat (R := ℤ) (A := F) m
    have h_coeff : PowerSeries.binomialSeries F (m : ℤ) = PowerSeries.mk fun k => (Ring.choose (m : ℤ) k : F) := by
      ext k
      simp [PowerSeries.binomialSeries_coeff, PowerSeries.coeff_mk, zsmul_one]
    calc
      ((1 : PowerSeries F) + PowerSeries.X) ^ (m : ℤ) = ((1 : PowerSeries F) + PowerSeries.X) ^ m := by simp
      _ = PowerSeries.binomialSeries F (m : ℤ) := by rw [h_binom]
      _ = PowerSeries.mk fun k => (Ring.choose (m : ℤ) k : F) := h_coeff
  | -[n+1] =>
    rw [zpow_neg, zpow_coe_nat]
    exact fps_onePlusX_pow_neg' (F := F) (n := n+1)
