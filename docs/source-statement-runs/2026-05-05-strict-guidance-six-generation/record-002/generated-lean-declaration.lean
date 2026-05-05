theorem fps_newton_binom (F : Type*) [Field F] [BinomialRing F] (n : ℤ) :
    (1 + PowerSeries.X : PowerSeries F) ^ n = PowerSeries.mk fun k => (Ring.choose (n : ℤ) k : F) := by
  by_cases hn : 0 ≤ n
  · lift n to ℕ using hn
    calc
      (1 + PowerSeries.X : PowerSeries F) ^ (n : ℤ) = (1 + PowerSeries.X : PowerSeries F) ^ (n : ℕ) := by simp
      _ = PowerSeries.binomialSeries F (n : ℤ) := by rw [← PowerSeries.binomialSeries_nat (R := ℤ) (A := F) n]
      _ = PowerSeries.mk fun k => (Ring.choose (n : ℤ) k : F) := rfl
  · have hpos : 0 ≤ -n := by linarith
    lift -n to ℕ using hpos with m hm
    have hn_eq : n = -(m : ℤ) := by linarith
    rw [hn_eq]
    have hcalc : (1 + PowerSeries.X : PowerSeries F) ^ (-(m : ℤ)) = ((1 + PowerSeries.X : PowerSeries F)⁻¹) ^ (m : ℕ) := by
      simp [zpow_neg, inv_pow]
    rw [hcalc, fps_onePlusX_pow_neg' F m]
