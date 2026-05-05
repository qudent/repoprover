theorem det_colop (A : Matrix (Fin n) (Fin n) K) (i j : Fin n) (hij : i ≠ j) : (A.submatrix id (Equiv.swap i j)).det = -A.det := by
  calc
    (A.submatrix id (Equiv.swap i j)).det = (A.submatrix id (Equiv.swap i j))ᵀ.det := by symm; apply Matrix.det_transpose
    _ = ((Aᵀ).submatrix (Equiv.swap i j) id).det := by
      simp [Matrix.submatrix_transpose]
    _ = -(Aᵀ).det := det_swap_rows (Aᵀ) i j hij
    _ = -A.det := by simp [Matrix.det_transpose]
