theorem isSummable_of_partial_sum_coeffStabilizesTo
    {f : ℕ → PowerSeries K} {lim : PowerSeries K}
    (h : CoeffStabilizesTo (fun i => ∑ j ∈ Finset.range (i + 1), f j) lim) :
    IsSummable f :=
  isSummable_of_coeffStabilizesTo_partial_sum h
