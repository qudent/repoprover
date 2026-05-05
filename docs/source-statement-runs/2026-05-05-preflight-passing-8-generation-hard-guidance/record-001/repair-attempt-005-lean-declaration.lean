theorem prop_fps_subs_rule_infprod {I : Type*} [DecidableEq I] (f : I → PowerSeries K) (g : PowerSeries K)
    (hg : constantCoeff g = 0) (hf_mulable : ∀ n, ∃ M : Finset I, ∀ J : Finset I, M ⊆ J → coeff n (∏ i ∈ J, f i) = coeff n (∏ i ∈ M, f i))
    (prod_f : PowerSeries K) (hprod : ∀ n (M : Finset I), (∀ J : Finset I, M ⊆ J → coeff n (∏ i ∈ J, f i) = coeff n (∏ i ∈ M, f i)) → coeff n prod_f = coeff n (∏ i ∈ M, f i)) : 
    ∀ n, ∃ M : Finset I, coeff n (prod_f.subst g) = coeff n (∏ i ∈ M, (f i).subst g) :=
by
  intro n
  choose M_k hM_k using hf_mulable
  let M := Finset.biUnion (Finset.range (n + 1)) M_k
  have hM_sub : ∀ k ≤ n, M_k k ⊆ M := by
    intro k hk
    apply Finset.subset_biUnion_of_mem
    simp [hk]
  have hM_approx : ∀ k ≤ n, ∀ J : Finset I, M ⊆ J → coeff k (∏ i ∈ J, f i) = coeff k (∏ i ∈ M, f i) := by
    intro k hk J hMJ
    have hMkJ : M_k k ⊆ J := (hM_sub k hk).trans hMJ
    rw [hM_k k J hMkJ]
    rw [hM_k k M (hM_sub k hk)]
  have hcoeff_prod_f : ∀ k ≤ n, coeff k prod_f = coeff k (∏ i ∈ M, f i) := by
    intro k hk
    refine hprod k M ?_
    intro J hMJ
    exact hM_approx k hk J hMJ
  have hsubst_coeff : coeff n (prod_f.subst g) = coeff n ((∏ i ∈ M, f i).subst g) :=
    xnEquiv_comp hcoeff_prod_f hg n (le_refl n)
  have hfin_subst : (∏ i ∈ M, f i).subst g = ∏ i ∈ M, (f i).subst g :=
    comp_prod_finite M f g hg
  rw [hfin_subst] at hsubst_coeff
  exact ⟨M, hsubst_coeff⟩
