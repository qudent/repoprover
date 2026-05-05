theorem product_lim_conv {f : ℕ → PowerSeries K} {lim : PowerSeries K}
    (h : CoeffStabilizesTo (fun i => ∏ j ∈ Finset.range (i + 1), f j) lim)
    (hconst : ∀ i, constantCoeff (f i) = 1) :
    IsMultipliable f ∧ tprod' f (isMultipliable_of_coeffStabilizesTo_partial_prod h hconst) = lim :=
  ⟨isMultipliable_of_coeffStabilizesTo_partial_prod h hconst,
    tprod'_eq_of_coeffStabilizesTo_partial_prod h hconst⟩
