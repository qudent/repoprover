theorem fps_subst_eq_mk_finsum (f g : K⟦X⟧) (hg : constantCoeff g = 0) : PowerSeries.subst g f = PowerSeries.mk (fun n => finsum (fun d => coeff d f * coeff n (g ^ d))) := by
  ext n
  rw [fps_comp_coeff f g hg n, coeff_mk]
