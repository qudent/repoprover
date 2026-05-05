theorem det_triang (A : Matrix (Fin n) (Fin n) K) (h : (∀ i j, j < i → A i j = 0) ∨ (∀ i j, i < j → A i j = 0)) : A.det = ∏ i, A i i := by
  rcases h with h_upper | h_lower
  · exact det_upperTriangular A h_upper
  · have h_transpose_upper : ∀ i j, j < i → (Aᵀ) i j = 0 := by
      intro i j hij
      have : (Aᵀ) i j = A j i := rfl
      rw [this]
      exact h_lower j i hij
    calc
      A.det = (Aᵀ).det := by rw [Matrix.det_transpose]
      _ = ∏ i, (Aᵀ) i i := det_upperTriangular Aᵀ h_transpose_upper
      _ = ∏ i, A i i := by simp
