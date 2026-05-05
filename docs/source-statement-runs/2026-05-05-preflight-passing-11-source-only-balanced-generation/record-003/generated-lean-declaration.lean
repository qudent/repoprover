theorem fps_newton_binom [Field K] [BinomialRing K] (n : ℤ) : (1 + PowerSeries.X : PowerSeries K) ^ n = PowerSeries.mk fun k => (Ring.choose n k : K) := by
  by_cases hn : 0 ≤ n
  · have hn_nonneg : ∃ (m : ℕ), (m : ℤ) = n :=
      ⟨n.toNat, Int.toNat_of_nonneg hn⟩
    rcases hn_nonneg with ⟨m, hm⟩
    have h_pow : (1 + PowerSeries.X : PowerSeries K) ^ n = (1 + PowerSeries.X : PowerSeries K) ^ (m : ℕ) := by
      rw [hm, zpow_natCast]
    have h_binom : (1 + PowerSeries.X : PowerSeries K) ^ (m : ℕ) = PowerSeries.binomialSeries K (m : ℤ) := by
      rw [PowerSeries.binomialSeries_nat (R := ℤ) (A := K) m]
    have h_mk : PowerSeries.binomialSeries K (m : ℤ) = PowerSeries.mk fun k => (Ring.choose (m : ℤ) k : K) := by
      ext k
      simp [PowerSeries.binomialSeries_coeff]
    rw [h_pow, h_binom, h_mk]
    simp [hm]
  · have hn_neg : n ≤ 0 := by linarith
    have hn_pos : 0 ≤ -n := by linarith
    have hm_ex : ∃ (m : ℕ), (m : ℤ) = -n :=
      ⟨(-n).toNat, Int.toNat_of_nonneg hn_pos⟩
    rcases hm_ex with ⟨m, hm⟩
    have hneg : n = - (m : ℤ) := by linarith
    have h_pow : (1 + PowerSeries.X : PowerSeries K) ^ n = ((1 + PowerSeries.X : PowerSeries K)⁻¹) ^ (m : ℕ) := by
      rw [hneg, zpow_neg, inv_zpow, zpow_natCast]
    have h_inv_pow : ((1 + PowerSeries.X : PowerSeries K)⁻¹) ^ (m : ℕ) = PowerSeries.mk fun k => (Ring.choose (-(m : ℤ)) k : K) := by
      rw [fps_onePlusX_pow_neg' (F := K) m]
    rw [h_pow, h_inv_pow]
    simp [hneg]
