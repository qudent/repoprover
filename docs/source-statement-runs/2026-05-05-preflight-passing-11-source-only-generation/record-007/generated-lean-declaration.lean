theorem summable_fps_comp (f g : K⟦X⟧) (hg : constantCoeff g = 0) :
    SummableFPS (fun n : ℕ => coeff n f • (g ^ n)) := by
  intro d
  have hzero : ∀ n, d < n → coeff d (coeff n f • (g ^ n)) = 0 := by
    intro n h
    rw [coeff_smul, fps_subs_wd_firstCoeffs g hg n d h, mul_zero]
  have h_fin : Set.Finite {n : ℕ | n ≤ d} := Set.finite_le_nat d
  have h_subset : {n : ℕ | coeff d (coeff n f • (g ^ n)) ≠ 0} ⊆ {n : ℕ | n ≤ d} := by
    intro n hn
    by_contra! h
    apply hn
    exact hzero n (Nat.lt_of_not_ge h)
  exact h_fin.subset h_subset
