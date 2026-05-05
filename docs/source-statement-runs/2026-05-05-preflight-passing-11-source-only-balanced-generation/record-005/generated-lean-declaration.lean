theorem exists_isXnApproximator_of_multipliable (a : I → PowerSeries R) (ha : Multipliable a) (n : ℕ) :
    ∃ M : Finset I, IsXnApproximator a M n :=
by
  let Mfm (m : ℕ) : Finset I := (ha m).choose
  have hMfm (m : ℕ) : DeterminesCoeffInProd a (Mfm m) m := (ha m).choose_spec
  let M := Finset.biUnion (Finset.range (n+1)) Mfm
  refine ⟨M, λ m hm => ?_⟩
  have hm_mem_range : m ∈ Finset.range (n+1) := Finset.mem_range.mpr (Nat.lt_succ_of_le hm)
  have hsub : Mfm m ⊆ M := Finset.subset_biUnion_of_mem Mfm hm_mem_range
  exact determinesCoeffInProd_mono (hMfm m) hsub
