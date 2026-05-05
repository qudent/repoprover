theorem fps_subst_X (g : K⟦X⟧) : PowerSeries.subst X g = g := by
  have hX : constantCoeff X = 0 := constantCoeff_X
  ext n
  rw [fps_comp_coeff_finite g X hX n]
  simp [coeff_X_pow, mul_ite, mul_one, mul_zero, Finset.sum_ite_eq, Finset.mem_range, Nat.lt_succ_self n]
