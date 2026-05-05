theorem det_add_smul_col (A : Matrix (Fin n) (Fin n) K) (i j : Fin n) (hij : i ≠ j) (c : K) :
    (A.updateCol i (fun k => A k i + c • A k j)).det = A.det := by
  have h_eq : (A.updateCol i (fun k => A k i + c • A k j)).transpose =
      (A.transpose).updateRow i (A.transpose i + c • A.transpose j) := by
    ext a b; simp [Matrix.updateCol, Matrix.transpose, Matrix.updateRow]
  rw [← Matrix.det_transpose, h_eq, det_add_smul_row A.transpose i j hij c, Matrix.det_transpose]
