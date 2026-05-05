lemma exists_isXnApproximator_of_multipliable {a : I → PowerSeries R} (ha : Multipliable a) (n : ℕ) : ∃ M : Finset I, IsXnApproximator a M n := by
  classical
  let M := Finset.biUnion (Finset.range (n+1)) (fun m => (ha m).choose)
  refine ⟨M, ?_⟩
  intro k hk
  have hk_range : k ∈ Finset.range (n+1) := Finset.mem_range.mpr (Nat.lt_succ_of_le hk)
  have hdeterm : DeterminesCoeffInProd a ((ha k).choose) k := (ha k).choose_spec
  have hsub : (ha k).choose ⊆ M := Finset.subset_biUnion_of_mem hk_range
  exact determinesCoeffInProd_mono hdeterm hsub
