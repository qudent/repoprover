theorem prop_fps_subs_rule_infprod {I : Type*} [DecidableEq I] (f : I → PowerSeries K) (g : PowerSeries K)
    (hg : constantCoeff g = 0) (hf_mulable : ∀ n, ∃ M : Finset I, ∀ J : Finset I, M ⊆ J → coeff n (∏ i ∈ J, f i) = coeff n (∏ i ∈ M, f i))
    (prod_f : PowerSeries K) (hprod : ∀ (n : ℕ) (M : Finset I), (∀ (J : Finset I), M ⊆ J → coeff n (∏ i ∈ J, f i) = coeff n (∏ i ∈ M, f i)) → coeff n prod_f = coeff n (∏ i ∈ M, f i)) :
    ∀ n, ∃ M : Finset I, (∀ J : Finset I, M ⊆ J → coeff n (∏ i ∈ J, (f i).subst g) = coeff n (∏ i ∈ M, (f i).subst g)) ∧ coeff n (prod_f.subst g) = coeff n (∏ i ∈ M, (f i).subst g) :=
by
  intro n
  choose M_k hM_k using hf_mulable
  let M := Finset.biUnion (Finset.range (n + 1)) M_k
  have hM_approx : ∀ k ≤ n, ∀ J : Finset I, M ⊆ J → coeff k (∏ i ∈ J, f i) = coeff k (∏ i ∈ M, f i) := by
    intro k hk J hMJ
    have hMk_sub : M_k k ⊆ M := by
      apply Finset.subset_biUnion_of_mem
      simp [hk]
    have hMkJ : M_k k ⊆ J := hMk_sub.trans hMJ
    calc
      coeff k (∏ i ∈ J, f i) = coeff k (∏ i ∈ M_k k, f i) := hM_k k J hMkJ
      _ = coeff k (∏ i ∈ M, f i) := (hM_k k M hMk_sub).symm
  have hcoeff_prod_f : ∀ k ≤ n, coeff k prod_f = coeff k (∏ i ∈ M, f i) := by
    intro k hk
    exact hprod k M (hM_approx k hk)
  have hcomp_approx : ∀ J : Finset I, M ⊆ J → coeff n (∏ i ∈ J, (f i).subst g) = coeff n (∏ i ∈ M, (f i).subst g) := by
    intro J hMJ
    apply comp_prod_approx_determines f g hg n M
    · exact hM_approx
    · exact hMJ
  have hsecond : coeff n (prod_f.subst g) = coeff n (∏ i ∈ M, (f i).subst g) := by
    have hequiv : coeff n (prod_f.subst g) = coeff n ((∏ i ∈ M, f i).subst g) :=
      xnEquiv_comp hcoeff_prod_f hg n (le_refl n)
    rw [hequiv, comp_prod_finite M f g hg]
  exact ⟨M, hcomp_approx, hsecond⟩
