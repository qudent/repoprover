lemma det_minors_diag {n : ℕ} (d : Fin n → R) (D : Matrix (Fin n) (Fin n) R) (hD : D = Matrix.diagonal d) :
    (∀ (P : Finset (Fin n)), (sub[P, P] D).det = ∏ i ∈ P, d i) ∧
    (∀ (P Q : Finset (Fin n)), P ≠ Q → (hcard : P.card = Q.card) → submatrixDet D P Q hcard = 0) :=
by
  constructor
  · intro P
    calc
      (sub[P, P] D).det = (sub[P, P] (Matrix.diagonal d)).det := by rw [hD]
      _ = (Matrix.diagonal (fun i : Fin P.card => d (P.orderEmbOfFin rfl i))).det := by
        have hsub_eq : sub[P, P] (Matrix.diagonal d) = Matrix.diagonal (fun i : Fin P.card => d (P.orderEmbOfFin rfl i)) := by
          ext i j
          simp [submatrixOfFinset_apply, Matrix.diagonal, (P.orderEmbOfFin rfl).injective.eq_iff]
        rw [hsub_eq]
      _ = ∏ i : Fin P.card, d (P.orderEmbOfFin rfl i) := Matrix.det_diagonal _
      _ = ∏ i ∈ P, d i := by
        apply Finset.prod_bij (fun i hi => P.orderEmbOfFin rfl i) ?_ ?_ ?_ ?_
        · intro i hi
          exact (P.orderEmbOfFin rfl i).2
        · intro i hi; rfl
        · intro i j hi hj h
          exact (P.orderEmbOfFin rfl).injective h
        · intro b hb
          have hbP : b ∈ P := hb
          let iso := Finset.orderIsoOfFin P rfl
          refine ⟨iso.symm ⟨b, hbP⟩, Finset.mem_univ _, ?_⟩
          dsimp [Finset.orderEmbOfFin, iso]
          simp
  · intro P Q hne hcard
    have h_exists : ∃ x ∈ P, x ∉ Q := by
      by_contra! h_all
      have hsub : P ⊆ Q := h_all
      have hcard_le : Q.card ≤ P.card := hcard.symm ▸ le_rfl
      have h_eq : P = Q := Finset.eq_of_subset_of_card_le hsub hcard_le
      exact hne h_eq
    rcases h_exists with ⟨x, hxP, hxQ⟩
    let isoP := Finset.orderIsoOfFin P rfl
    have hxP' : x ∈ (P : Finset (Fin n)) := hxP
    let ix := isoP.symm ⟨x, hxP'⟩
    have hx_val : P.orderEmbOfFin rfl ix = x := by
      dsimp [Finset.orderEmbOfFin, isoP]
      simp
    have hzero : (D.submatrix (P.orderEmbOfFin rfl) (Q.orderEmbOfFin (hcard ▸ rfl))).det = 0 := by
      apply Matrix.det_eq_zero_of_row_eq_zero ix
      intro j
      calc
        (D.submatrix (P.orderEmbOfFin rfl) (Q.orderEmbOfFin (hcard ▸ rfl))) ix j
            = D (P.orderEmbOfFin rfl ix) (Q.orderEmbOfFin (hcard ▸ rfl) j) := rfl
        _ = (Matrix.diagonal d) (P.orderEmbOfFin rfl ix) (Q.orderEmbOfFin (hcard ▸ rfl) j) := by rw [hD]
        _ = d (P.orderEmbOfFin rfl ix) * (if P.orderEmbOfFin rfl ix = Q.orderEmbOfFin (hcard ▸ rfl) j then 1 else 0) :=
          by rw [Matrix.diagonal_apply]
        _ = 0 := by
          have hneq : P.orderEmbOfFin rfl ix ≠ Q.orderEmbOfFin (hcard ▸ rfl) j := by
            intro heq
            apply hxQ
            have memQ : (Q.orderEmbOfFin (hcard ▸ rfl) j) ∈ Q := (Q.orderEmbOfFin (hcard ▸ rfl) j).2
            rw [← heq, hx_val] at memQ
            exact memQ
          simp [hneq]
    dsimp [submatrixDet]
    exact hzero
