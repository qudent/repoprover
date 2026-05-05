theorem det_colop (A : Matrix (Fin n) (Fin n) K) (i j : Fin n) (hij : i ≠ j) (c : K) :
    (A.submatrix id (Equiv.swap i j)).det = -A.det ∧
    (A.updateCol i (fun r => A r i + A r j)).det = A.det ∧
    (A.updateCol i (fun r => A r i + c • (A r j))).det = A.det :=
by
  have h_swap : (A.submatrix id (Equiv.swap i j)).det = -A.det := det_swap_cols A i j hij
  have h_add : (A.updateCol i (fun r => A r i + A r j)).det = A.det := by
    have h : (A.transpose.updateRow i (A.transpose i + A.transpose j)).transpose = A.updateCol i (fun r => A r i + A r j) := by
      ext r s; simp [Matrix.updateRow, Matrix.updateCol, Matrix.transpose, Pi.add_apply]
    calc
      (A.updateCol i (fun r => A r i + A r j)).det = ((A.transpose.updateRow i (A.transpose i + A.transpose j)).transpose).det := by rw [h]
      _ = (A.transpose.updateRow i (A.transpose i + A.transpose j)).det := by rw [Matrix.det_transpose]
      _ = A.transpose.det := by rw [det_add_row (A.transpose) i j hij]
      _ = A.det := by rw [Matrix.det_transpose]
  have h_add_smul : (A.updateCol i (fun r => A r i + c • (A r j))).det = A.det := by
    have h : (A.transpose.updateRow i (A.transpose i + c • (A.transpose j))).transpose = A.updateCol i (fun r => A r i + c • (A r j)) := by
      ext r s; simp [Matrix.updateRow, Matrix.updateCol, Matrix.transpose, Pi.add_apply, smul_eq_mul]
    calc
      (A.updateCol i (fun r => A r i + c • (A r j))).det = ((A.transpose.updateRow i (A.transpose i + c • (A.transpose j))).transpose).det := by rw [h]
      _ = (A.transpose.updateRow i (A.transpose i + c • (A.transpose j))).det := by rw [Matrix.det_transpose]
      _ = A.transpose.det := by rw [det_add_smul_row (A.transpose) i j hij c]
      _ = A.det := by rw [Matrix.det_transpose]
  exact ⟨h_swap, h_add, h_add_smul⟩
