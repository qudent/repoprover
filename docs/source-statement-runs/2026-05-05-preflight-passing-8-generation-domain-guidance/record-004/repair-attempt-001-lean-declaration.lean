theorem fps_subst_X (g : K⟦X⟧) : PowerSeries.subst X g = g := by
  have hX : constantCoeff (X : K⟦X⟧) = 0 := by simp
  ext n
  rw [fps_comp_coeff g X hX n]
  have hzero : ∀ d, d ≠ n → coeff d g * coeff n (X ^ d) = 0 := by
    intro d hdne
    simp [coeff_X_pow, hdne]
  rw [finsum_eq_single (fun d => coeff d g * coeff n (X ^ d)) n hzero]
  simp
