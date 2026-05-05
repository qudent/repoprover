theorem det_swap_cols (A : Matrix (Fin n) (Fin n) K) (i j : Fin n) (hij : i ≠ j) :
    (A.submatrix id (Equiv.swap i j)).det = -A.det :=
  calc
    (A.submatrix id (Equiv.swap i j)).det = ((A.submatrix id (Equiv.swap i j)).transpose).det := by
      simpa using (Matrix.det_transpose (A.submatrix id (Equiv.swap i j))).symm
    _ = (A.transpose.submatrix (Equiv.swap i j) id).det := by simp [Matrix.submatrix_transpose]
    _ = -(A.transpose).det := by simpa using det_swap_rows (A.transpose) i j hij
    _ = -A.det := by simp [Matrix.det_transpose]
