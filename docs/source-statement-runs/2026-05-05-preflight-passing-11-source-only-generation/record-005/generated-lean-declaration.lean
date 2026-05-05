theorem exists_isXnApproximator_of_multipliable {a : I → PowerSeries R} (ha : Multipliable a) (n : ℕ) : ∃ M : Finset I, IsXnApproximator a M n := by
  classical
    let M : ℕ → Finset I := fun m => (ha m).choose
    have hM_spec (m : ℕ) : DeterminesCoeffInProd a (M m) m := (ha m).choose_spec
    let M_all : Finset I := Finset.biUnion (Finset.range (n + 1)) M
    refine ⟨M_all, ?_⟩
    intro m hm
    have hmem_range : m ∈ Finset.range (n + 1) := Finset.mem_range.2 (Nat.lt_succ_of_le hm)
    have h_sub : M m ⊆ M_all := Finset.subset_biUnion_of_mem hmem_range
    exact determinesCoeffInProd_mono (hM_spec m) h_sub
