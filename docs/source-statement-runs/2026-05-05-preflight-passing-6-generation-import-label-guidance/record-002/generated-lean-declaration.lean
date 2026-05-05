theorem det_swap_cols (A : Matrix (Fin n) (Fin n) K) (i j : Fin n) (hij : i ≠ j) : (A.submatrix id (Equiv.swap i j)).det = -A.det := by
  have h_trans : (A.submatrix id (Equiv.swap i j))ᵀ = (Aᵀ).submatrix (Equiv.swap i j) id := by
    ext r c
    simp [submatrix_apply, transpose_apply]
  calc
    (A.submatrix id (Equiv.swap i j)).det = ((A.submatrix id (Equiv.swap i j))ᵀ).det := by rw [Matrix.det_transpose]
    _ = ((Aᵀ).submatrix (Equiv.swap i j) id).det := by rw [h_trans]
    _ = - ((Aᵀ).det) := by
      simpa using det_swap_rows (Aᵀ) i j hij
    _ = -A.det := by rw [Matrix.det_transpose]
