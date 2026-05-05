theorem coeffFinitelyDeterminedInProd_of_finite [Fintype I] (a : I → PowerSeries R) (n : ℕ) :
    CoeffFinitelyDeterminedInProd a n := by
  refine ⟨Finset.univ, ?_⟩
  intro J hJ
  have h_eq : J = Finset.univ := Finset.Subset.antisymm (Finset.subset_univ J) hJ
  subst h_eq
  rfl
