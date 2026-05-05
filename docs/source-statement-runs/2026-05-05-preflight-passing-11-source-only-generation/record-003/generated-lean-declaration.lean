theorem fps_onePlusX_pow_int {F : Type*} [Field F] [BinomialRing F] (n : ℤ) :
    (1 + PowerSeries.X : PowerSeries F) ^ n =
      PowerSeries.mk fun k => (Ring.choose n k : F) := by
  by_cases h : 0 ≤ n
  · lift n to ℕ using h
    simpa [zpow_coe_nat] using PowerSeries.binomialSeries_nat (R := ℤ) (A := F) n
  · have h_nonpos : n ≤ 0 := by linarith
    have hn_eq : n = - (Int.natAbs n : ℤ) := by
      simpa [Int.natAbs_of_nonpos h_nonpos]
    rw [hn_eq, zpow_neg, zpow_coe_nat, fps_onePlusX_pow_neg' F (Int.natAbs n)]
