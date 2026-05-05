theorem fps_subs_X_right (g : K⟦X⟧) : PowerSeries.subst (X : K⟦X⟧) g = g := by
  have hX0 : constantCoeff (X : K⟦X⟧) = 0 := by simp
  ext n
  rw [fps_comp_coeff g (X : K⟦X⟧) hX0 n]
  apply finsum_eq_single (fun d => coeff d g * coeff n (X ^ d)) n ?_ ?_
  · intro d hd
    simp [hd, coeff_X_pow]
  · simp
