theorem fps_subs_X_right (g : K⟦X⟧) : PowerSeries.subst (X : K⟦X⟧) g = g := by
  have hX0 : constantCoeff (X : K⟦X⟧) = 0 := by simp
  have ha := HasSubst.of_constantCoeff_zero' hX0
  ext n
  rw [coeff_subst' ha g n]
  apply finsum_eq_single (f := fun d ↦ coeff d g * coeff n (X ^ d)) (a := n)
  intro b hb
  simp [hb, coeff_X_pow]
