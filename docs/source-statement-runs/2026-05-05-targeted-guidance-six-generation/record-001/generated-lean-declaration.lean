theorem sum_lim_conv {f : ℕ → PowerSeries K} {L : PowerSeries K}
    (h : CoeffStabilizesTo (fun i => ∑ j ∈ Finset.range (i + 1), f j) L) :
    IsSummable f ∧ tsum' f (isSummable_of_coeffStabilizesTo_partial_sum h) = L :=
by
  have h_summable : IsSummable f := isSummable_of_coeffStabilizesTo_partial_sum h
  have h_eq : tsum' f h_summable = L := tsum'_eq_of_coeffStabilizesTo_partial_sum h
  exact And.intro h_summable h_eq
