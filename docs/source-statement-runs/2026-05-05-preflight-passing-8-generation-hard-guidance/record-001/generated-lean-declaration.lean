theorem prop_fps_subs_rule_infprod {I : Type*} [DecidableEq I] (f : I → PowerSeries K) (g : PowerSeries K)
    (hg : constantCoeff g = 0) (hf_mulable : ∀ n, ∃ M : Finset I, ∀ J : Finset I, M ⊆ J → coeff n (∏ i ∈ J, f i) = coeff n (∏ i ∈ M, f i))
    (prod_f : PowerSeries K) (hprod : ∀ n, ∃ M : Finset I, (∀ J : Finset I, M ⊆ J → coeff n (∏ i ∈ J, f i) = coeff n (∏ i ∈ M, f i)) ∧ coeff n prod_f = coeff n (∏ i ∈ M, f i)) :
    ∀ n, ∃ M : Finset I, (∀ J : Finset I, M ⊆ J → coeff n (∏ i ∈ J, (f i).subst g) = coeff n (∏ i ∈ M, (f i).subst g)) ∧ coeff n (prod_f.subst g) = coeff n (∏ i ∈ M, (f i).subst g) := by
  intro n
  choose M_f hM_f using hf_mulable
  let M := Finset.biUnion (Finset.range (n + 1)) M_f
  have hM_sub : ∀ k ≤ n, M_f k ⊆ M := by
    intro k hk
    apply Finset.subset_biUnion_of_mem
    simp [hk]
  have hM_approx : ∀ k ≤ n, ∀ J : Finset I, M ⊆ J → coeff k (∏ i ∈ J, f i) = coeff k (∏ i ∈ M, f i) := by
    intro k hk J hMJ
    have hMkJ : M_f k ⊆ J := (hM_sub k hk).trans hMJ
    rw [hM_f k J hMkJ]
    rw [hM_f k M (hM_sub k hk)]
  have hcoeff_prod_f : ∀ k ≤ n, coeff k prod_f = coeff k (∏ i ∈ M, f i) := by
    intro k hk
    rcases hprod k with ⟨M_prod, hMproj, hcoeff⟩
    have htemp1 : M_f k ⊆ M_f k ∪ M_prod := Finset.subset_union_left _ _
    have htemp2 : M_prod ⊆ M_f k ∪ M_prod := Finset.subset_union_right _ _
    have htemp5 : coeff k (∏ i ∈ M_f k, f i) = coeff k (∏ i ∈ M_prod, f i) := by
      calc
        coeff k (∏ i ∈ M_f k, f i) = coeff k (∏ i ∈ M_f k ∪ M_prod, f i) := (hM_f k (M_f k ∪ M_prod) htemp1).symm
        _ = coeff k (∏ i ∈ M_prod, f i) := hMproj (M_f k ∪ M_prod) htemp2
    have htemp6 : coeff k (∏ i ∈ M_f k, f i) = coeff k (∏ i ∈ M, f i) := hM_f k M (hM_sub k hk)
    calc
      coeff k prod_f = coeff k (∏ i ∈ M_prod, f i) := hcoeff
      _ = coeff k (∏ i ∈ M_f k, f i) := htemp5.symm
      _ = coeff k (∏ i ∈ M, f i) := htemp6
  have hcomp_approx : ∀ J : Finset I, M ⊆ J → coeff n (∏ i ∈ J, (f i).subst g) = coeff n (∏ i ∈ M, (f i).subst g) := by
    intro J hMJ
    apply comp_prod_approx_determines f g hg n M
    · intro k hk J' hMJ'
      exact hM_approx k hk J' hMJ'
    · exact hMJ
  have hsecond : coeff n (prod_f.subst g) = coeff n (∏ i ∈ M, (f i).subst g) := by
    have hequiv : coeff n (prod_f.subst g) = coeff n ((∏ i ∈ M, f i).subst g) :=
      xnEquiv_comp hcoeff_prod_f hg n (le_refl n)
    rw [hequiv]
    rw [comp_prod_finite M f g hg]
  exact ⟨M, hcomp_approx, hsecond⟩
