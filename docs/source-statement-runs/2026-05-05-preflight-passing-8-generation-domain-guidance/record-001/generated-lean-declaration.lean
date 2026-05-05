theorem subst_tprod {I : Type*} (f : I → PowerSeries K) (g : PowerSeries K) (hg : constantCoeff g = 0) (hf : Multipliable f) : (∏' i, f i).subst g = ∏' i, (f i).subst g := by
  have hSubst : HasSubst g := HasSubst.of_constantCoeff_zero' hg
  have h_cont : Continuous (subst g) := continuous_subst hSubst
  simpa using hf.map_tprod (subst g) h_cont
