theorem fps_subs_X_right (g : K⟦X⟧) : PowerSeries.subst (X : K⟦X⟧) g = g := by
  have hX0 : constantCoeff (X : K⟦X⟧) = 0 := by simp
  have ha := HasSubst.of_constantCoeff_zero' hX0
  ext n
  rw [coeff_subst' ha g n]
  refine finsum_eq_single (f := fun d => coeff d g * coeff n (X ^ d)) (a := n) ?_ ?_
  · intro d hd
    simp [hd, coeff_X_pow]
  · simp
