theorem det_colop : 
    (∀ (A : Matrix (Fin n) (Fin n) K) (i j : Fin n), i ≠ j → det (A.submatrix id (Equiv.swap i j)) = -det A) ∧
    (∀ (A : Matrix (Fin n) (Fin n) K) (i : Fin n) (c : K), det (A.updateColumn i (λ k => c * A k i)) = c * det A) ∧
    (∀ (A : Matrix (Fin n) (Fin n) K) (i j : Fin n) (h : i ≠ j) (c : K), det (A.updateColumn i (λ k => A k i + c * A k j)) = det A) :=
by
  refine ⟨?hswap, ?hscale, ?hadd⟩
  · intro A i j h
    calc
      det (A.submatrix id (Equiv.swap i j)) = det ((A.submatrix id (Equiv.swap i j))ᵀ) := by rw [Matrix.det_transpose]
      _ = det (Matrix.of (Aᵀ ∘ Equiv.swap i j)) := by
        ext m n; simp
      _ = -det (Aᵀ) := by rw [det_swap_rows (Aᵀ) i j h]
      _ = -det A := by rw [Matrix.det_transpose]
  · intro A i c
    calc
      det (A.updateColumn i (λ k => c * A k i)) = det ((A.updateColumn i (λ k => c * A k i))ᵀ) := by rw [Matrix.det_transpose]
      _ = det ((Aᵀ).updateRow i (λ j => c * (Aᵀ i j))) := by
        ext m n; simp
      _ = det ((Aᵀ).updateRow i (c • (Aᵀ i))) := by
        ext m n; simp
      _ = c * det (Aᵀ) := by rw [det_scale_row (Aᵀ) i c]
      _ = c * det A := by rw [Matrix.det_transpose]
  · intro A i j h c
    calc
      det (A.updateColumn i (λ k => A k i + c * A k j)) = det ((A.updateColumn i (λ k => A k i + c * A k j))ᵀ) := by rw [Matrix.det_transpose]
      _ = det ((Aᵀ).updateRow i (Aᵀ i + c • Aᵀ j)) := by
        ext m n; simp [Pi.add_apply, smul_eq_mul]
      _ = det (Aᵀ) := by rw [det_add_smul_row (Aᵀ) i j h c]
      _ = det A := by rw [Matrix.det_transpose]
