theorem partialSum_coeffStabilizesTo (f : ℕ → PowerSeries K) (hf : IsSummable f) :
    CoeffStabilizesTo (fun i => ∑ j ∈ Finset.range (i + 1), f j) (tsum' f hf) :=
  coeffStabilizesTo_partial_sum hf
