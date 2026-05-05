theorem subst_tprod {I : Type*} [DecidableEq I] (f : I → PowerSeries K) (g : PowerSeries K) (hg : constantCoeff g = 0)
  (hf : Multipliable f) : (∏' i, f i).subst g = ∏' i, (f i).subst g := by
  have hf_approx : ∀ n, ∃ M : Finset I, ∀ J : Finset I, M ⊆ J → coeff n (∏ i∈J, f i) = coeff n (∏ i∈M, f i) :=
    fun n => hf.exists_approx n
  have hcomp_approx : ∀ n, ∃ M : Finset I, ∀ J : Finset I, M ⊆ J → coeff n (∏ i∈J, (f i).subst g) = coeff n (∏ i∈M, (f i).subst g) :=
    comp_prod_multipliable f g hg hf_approx
  have h_comp_mul : Multipliable (fun i : I => (f i).subst g) :=
    Multipliable.mk hcomp_approx
  ext n
  have h_approx_all : ∃ M : Finset I, ∀ k ≤ n, ∀ J : Finset I, M ⊆ J → coeff k (∏ i∈J, f i) = coeff k (∏ i∈M, f i) := by
    choose M_k hM_k using hf_approx
    use Finset.biUnion (Finset.range (n+1)) M_k
    intro k hk J hJ
    have hMk_sub : M_k k ⊆ Finset.biUnion (Finset.range (n+1)) M_k := by
      apply Finset.subset_biUnion_of_mem; simp [hk]
    exact hM_k k J (hMk_sub.trans hJ)
  rcases h_approx_all with ⟨M, hMall⟩
  have hMall_n : ∀ J : Finset I, M ⊆ J → coeff n (∏ i∈J, f i) = coeff n (∏ i∈M, f i) :=
    fun J hMJ => hMall n (le_refl n) J hMJ
  have hcoeff_tprod_f : coeff n (∏' i, f i) = coeff n (∏ i∈M, f i) :=
    hf.coeff_tprod n M hMall_n
  have hcoeff_tprod_comp : coeff n (∏' i, (f i).subst g) = coeff n (∏ i∈M, (f i).subst g) := by
    have h_act : ∀ J : Finset I, M ⊆ J → coeff n (∏ i∈J, (f i).subst g) = coeff n (∏ i∈M, (f i).subst g) := by
      intro J hMJ
      apply comp_prod_approx_determines f g hg n M (fun k hk J' hMJ' => hMall k hk J' hMJ') J hMJ
    apply h_comp_mul.coeff_tprod n M h_act
  have h_equality_up_to_n : ∀ k ≤ n, coeff k (∏' i, f i) = coeff k (∏ i∈M, f i) := by
    intro k hk
    have hMall_k : ∀ J : Finset I, M ⊆ J → coeff k (∏ i∈J, f i) = coeff k (∏ i∈M, f i) :=
      fun J hMJ => hMall k hk J hMJ
    exact hf.coeff_tprod k M hMall_k
  have hn_eq : coeff n ((∏' i, f i).subst g) = coeff n ((∏ i∈M, f i).subst g) :=
    (xnEquiv_comp h_equality_up_to_n hg n (le_refl n)) n (le_refl n)
  rw [hn_eq]
  rw [comp_prod_finite M f g hg]
  rw [hcoeff_tprod_comp]
