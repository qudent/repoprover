lemma det_minors_diag {n : ℕ} (d : Fin n → R) : (∀ P : Finset (Fin n), det (sub[P,P] (Matrix.diagonal d)) = ∏ i ∈ P, d i) ∧
    (∀ (P Q : Finset (Fin n)), P ≠ Q → P.card = Q.card → det (sub[P,Q] (Matrix.diagonal d)) = 0) :=
by
  have hsubdiag (P : Finset (Fin n)) : sub[P,P] (Matrix.diagonal d) = Matrix.diagonal (fun i : Fin P.card => d (P.orderEmbOfFin rfl i)) := by
    have hinj : Function.Injective (P.orderEmbOfFin rfl) := (P.orderEmbOfFin rfl).injective
    ext i j
    simp [submatrixOfFinset_apply, Matrix.diagonal, hinj.eq_iff]
  have hprodeq (P : Finset (Fin n)) : (∏ i : Fin P.card, d (P.orderEmbOfFin rfl i)) = ∏ i ∈ P, d i := by
    calc
      (∏ i : Fin P.card, d (P.orderEmbOfFin rfl i)) = ∏ i in (Finset.univ : Finset (Fin P.card)), d ((P.orderEmbOfFin rfl) i) := by simp
      _ = ∏ i in Finset.image (P.orderEmbOfFin rfl) Finset.univ, d i :=
        (Finset.prod_image (P.orderEmbOfFin rfl).injective).symm
      _ = ∏ i ∈ P, d i := by
        rw [Finset.image_eq_map_of_injective (P.orderEmbOfFin rfl).injective, Finset.map_orderEmbOfFin P rfl]
  have himage (P : Finset (Fin n)) : Finset.image (P.orderEmbOfFin rfl) (Finset.univ : Finset (Fin P.card)) = P := by
    rw [Finset.image_eq_map_of_injective (P.orderEmbOfFin rfl).injective, Finset.map_orderEmbOfFin P rfl]
  refine ⟨?_, ?_⟩
  · intro P
    rw [hsubdiag P]
    rw [Matrix.det_diagonal]
    exact hprodeq P
  · intro P Q hne hcard
    have h_nonempty : (P \ Q).Nonempty := by
      by_contra h_empty
      have h_empty' : P \ Q = ∅ := Finset.not_nonempty_iff_eq_empty.mp h_empty
      have h_sub : P ⊆ Q := Finset.sdiff_eq_empty_iff_subset.mp h_empty'
      have h_card_sub : P.card ≤ Q.card := Finset.card_le_card_of_subset h_sub
      have h_card_eq' : P.card = Q.card := hcard
      have : P = Q := Finset.eq_of_subset_of_card_le h_sub (by rw [h_card_eq']; exact le_rfl)
      exact hne this
    rcases h_nonempty with ⟨i, hi⟩
    have hi_P : i ∈ P := hi.1
    have hi_notQ : i ∉ Q := hi.2
    have hmem : i ∈ Finset.image (P.orderEmbOfFin rfl) (Finset.univ : Finset (Fin P.card)) := by
      rw [himage P]
      exact hi_P
    rcases Finset.mem_image.mp hmem with ⟨k, hk_mem, hk_eq⟩
    have h_row_zero : ∀ (j : Fin Q.card), sub[P,Q] (Matrix.diagonal d) k j = 0 := by
      intro j
      rw [submatrixOfFinset_apply]
      rw [hk_eq]
      have h_ne : i ≠ Q.orderEmbOfFin rfl j := by
        intro h_eq
        apply hi_notQ
        rw [h_eq]
        have : Q.orderEmbOfFin rfl j ∈ Q := by
          rw [← himage Q]
          exact Finset.mem_image.mpr ⟨j, Finset.mem_univ _, rfl⟩
        exact this
      simp [Matrix.diagonal, h_ne]
    rw [Matrix.det_eq_zero_of_row_eq_zero _ k h_row_zero]
