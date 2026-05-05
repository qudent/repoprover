theorem det_lowerTriangular (A : Matrix (Fin n) (Fin n) K) (hA : ∀ i j, i < j → A i j = 0) : A.det = ∏ i, A i i := by
  calc
    A.det = Aᵀ.det := by rw [Matrix.det_transpose]
    _ = ∏ i, Aᵀ i i := det_upperTriangular Aᵀ (fun i j hji => hA j i hji)
    _ = ∏ i, A i i := by simp
