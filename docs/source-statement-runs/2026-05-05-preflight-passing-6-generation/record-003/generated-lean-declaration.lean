theorem det_colop (A : Matrix (Fin n) (Fin n) K) (i j : Fin n) (hij : i ≠ j) (c : K) :
    (A.submatrix id (Equiv.swap i j)).det = -A.det ∧
    ((∀ k, A k j = 0) → A.det = 0) ∧
    ((A.updateColumn j (A · j + c • A · i)).det = A.det) ∧
    ((A.updateColumn j (c • A · j)).det = c * A.det) :=
by
  have hswap : (A.submatrix id (Equiv.swap i j)).det = -A.det :=
    det_swap_cols A i j hij
  have hzero : (∀ k, A k j = 0) → A.det = 0 := by
    intro h
    have hrow : ∀ k, A.transpose j k = 0 := by
      intro k; simpa [Matrix.transpose] using h k
    rw [← Matrix.det_transpose A, det_zero_row A.transpose j hrow]
  have hadd : (A.updateColumn j (A · j + c • A · i)).det = A.det := by
    calc
      (A.updateColumn j (A · j + c • A · i)).det
          = (A.updateColumn j (A · j + c • A · i)).transpose.det := by rw [Matrix.det_transpose]
      _ = (A.transpose.updateRow j (A.transpose j + c • A.transpose i)).det := by
        ext a b; simp [Matrix.updateColumn, Matrix.transpose, Matrix.updateRow]
      _ = A.transpose.det := det_add_mul_row A.transpose i j hij c
      _ = A.det := by rw [Matrix.det_transpose]
  have hmul : (A.updateColumn j (c • A · j)).det = c * A.det := by
    calc
      (A.updateColumn j (c • A · j)).det
          = (A.updateColumn j (c • A · j)).transpose.det := by rw [Matrix.det_transpose]
      _ = (A.transpose.updateRow j (c • A.transpose j)).det := by
        ext a b; simp [Matrix.updateColumn, Matrix.transpose, Matrix.updateRow]
      _ = c * A.transpose.det := det_mul_row A.transpose j c
      _ = c * A.det := by rw [Matrix.det_transpose]
  exact And.intro hswap (And.intro hzero (And.intro hadd hmul))
