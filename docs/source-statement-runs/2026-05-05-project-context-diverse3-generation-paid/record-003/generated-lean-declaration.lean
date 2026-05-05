theorem laupol_ring : (CommAlgebra K K[T;T⁻¹]) ∧ (1 : K[T;T⁻¹]) = T 0 ∧ IsUnit (T 1 : K[T;T⁻¹]) := by
  refine ⟨?_, ?_, ?_⟩
  · exact inferInstance
  · exact (laurentPolynomial_one_eq_T_zero K)
  · exact T_isUnit
