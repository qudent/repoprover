theorem sum_lim_conv {f : ℕ → PowerSeries K} {L : PowerSeries K} (h : CoeffStabilizesTo (fun i => ∑ j ∈ Finset.range (i + 1), f j) L) : IsSummable f ∧ tsum' f (⟨L, h⟩ : IsSummable f) = L :=
by
  have hsum : IsSummable f := ⟨L, h⟩
  refine ⟨hsum, ?_⟩
  rfl
