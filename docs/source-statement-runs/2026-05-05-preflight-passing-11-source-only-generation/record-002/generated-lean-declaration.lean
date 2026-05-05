theorem det_triangular (A : Matrix (Fin n) (Fin n) K) (h : (∀ i j, j < i → A i j = 0) ∨ (∀ i j, i < j → A i j = 0)) : A.det = ∏ i, A i i := by
  rcases h with (hU | hL)
  · exact det_upperTriangular A hU
  · have hU' : (∀ i j, j < i → (A.transpose) i j = 0) := by
      intro i j hij
      simpa using hL j i hij
    calc
      A.det = det (A.transpose) := by rw [← Matrix.det_transpose A]
      _ = ∏ i, (A.transpose) i i := det_upperTriangular (A.transpose) hU'
      _ = ∏ i, A i i := by simp
