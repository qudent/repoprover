theorem det_add_smul_col (A : Matrix (Fin n) (Fin n) K) (i j : Fin n) (hij : i ≠ j) (c : K) :
    (A.updateCol i (fun k => A k i + c • A k j)).det = A.det := by
  have htrans : (A.updateCol i (fun k => A k i + c • A k j)).transpose =
      A.transpose.updateRow i ((A.transpose) i + c • (A.transpose) j) := by
    ext a b
    by_cases h : a = i
    · simp [h, Matrix.updateCol_apply, Matrix.updateRow_apply, Matrix.transpose_apply]
    · simp [h, Matrix.updateCol_apply, Matrix.updateRow_apply, Matrix.transpose_apply]
  calc
    (A.updateCol i (fun k => A k i + c • A k j)).det = (A.updateCol i (fun k => A k i + c • A k j)).transpose.det := by
      rw [Matrix.det_transpose]
    _ = (A.transpose.updateRow i ((A.transpose) i + c • (A.transpose) j)).det := by rw [htrans]
    _ = A.transpose.det := by rw [det_add_smul_row (A.transpose) i j hij c]
    _ = A.det := by rw [Matrix.det_transpose]
