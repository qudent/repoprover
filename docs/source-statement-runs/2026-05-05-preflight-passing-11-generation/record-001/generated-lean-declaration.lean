theorem summable_and_tsum'_eq_of_coeffStabilizesTo_partial_sum
    {f : ℕ → PowerSeries K} {L : PowerSeries K}
    (h : CoeffStabilizesTo (fun i => ∑ j ∈ Finset.range (i + 1), f j) L) :
    IsSummable f ∧ tsum' f (isSummable_of_coeffStabilizesTo_partial_sum h) = L :=
  And.intro (isSummable_of_coeffStabilizesTo_partial_sum h)
    (tsum'_eq_of_coeffStabilizesTo_partial_sum h)
