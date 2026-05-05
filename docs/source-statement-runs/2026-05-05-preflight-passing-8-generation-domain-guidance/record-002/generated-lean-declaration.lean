theorem det_swap_cols (A : Matrix (Fin n) (Fin n) K) (i j : Fin n) (hij : i ≠ j) :
    (A.submatrix id (Equiv.swap i j)).det = -A.det := by
  have h_trans : (A.submatrix id (Equiv.swap i j))ᵀ = Aᵀ.submatrix (Equiv.swap i j) id := by
    ext i' j'; simp [Matrix.submatrix_apply]
  have h_eq : Aᵀ.submatrix (Equiv.swap i j) id = Matrix.of (Aᵀ ∘ Equiv.swap i j) := by
    ext i' j'; simp [Matrix.submatrix_apply, Matrix.of_apply]
  calc
    (A.submatrix id (Equiv.swap i j)).det = ((A.submatrix id (Equiv.swap i j))ᵀ).det := by rw [Matrix.det_transpose]
    _ = (Aᵀ.submatrix (Equiv.swap i j) id).det := by rw [h_trans]
    _ = (Matrix.of (Aᵀ ∘ Equiv.swap i j)).det := by rw [h_eq]
    _ = -(Aᵀ).det := by rw [det_swap_rows Aᵀ i j hij]
    _ = -A.det := by rw [Matrix.det_transpose]
