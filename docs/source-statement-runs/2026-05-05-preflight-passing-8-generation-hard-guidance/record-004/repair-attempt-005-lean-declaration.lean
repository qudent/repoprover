theorem fps_subs_X_right (g : K⟦X⟧) : PowerSeries.subst (X : K⟦X⟧) g = g := by
  have ha : HasSubst (X : K⟦X⟧) := HasSubst.of_constantCoeff_zero' (by simp)
  ext n
  rw [coeff_subst' ha g n]
  simp only [coeff_X_pow, smul_eq_mul]
  rw [finsum_eq_single (fun d => coeff d g * coeff n (X ^ d)) n (by
    intro d hd
    simp [hd.symm, coeff_X_pow])
  ]
  simp
