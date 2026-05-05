theorem det_colop (A : Matrix (Fin n) (Fin n) K) (i j : Fin n) (hij : i ≠ j) (c : K) :
    (A.submatrix id (Equiv.swap i j)).det = -A.det ∧
    (A.updateCol i (fun k => A k i + c • A k j)).det = A.det :=
by
  have hswap : (A.submatrix id (Equiv.swap i j)).det = -A.det := det_swap_cols A i j hij
  have hadd : (A.updateCol i (fun k => A k i + c • A k j)).det = A.det := by
    have h_eq : (A.updateCol i (fun k => A k i + c • A k j)).transpose =
        A.transpose.updateRow i (A.transpose i + c • A.transpose j) := by
      ext a b
      simp [Matrix.transpose, Matrix.updateCol, Matrix.updateRow]
    calc
      (A.updateCol i (fun k => A k i + c • A k j)).det = 
          (A.updateCol i (fun k => A k i + c • A k j)).transpose.det := by rw [Matrix.det_transpose]
      _ = (A.transpose.updateRow i (A.transpose i + c • A.transpose j)).det := by rw [h_eq]
      _ = A.transpose.det := by rw [det_add_smul_row (A.transpose) i j hij c]
      _ = A.det := by rw [Matrix.det_transpose]
  exact And.intro hswap hadd
