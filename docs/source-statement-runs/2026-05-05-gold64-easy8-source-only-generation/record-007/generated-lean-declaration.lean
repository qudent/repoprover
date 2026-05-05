lemma inverse_unique {a b c : L} (hab : a * b = 1) (hac : a * c = 1) : b = c :=
  calc
    b = 1 * b := by simp
    _ = (a * c) * b := by rw [← hac, mul_comm]
    _ = (c * a) * b := by rw [mul_comm a c]
    _ = c * (a * b) := by simp [mul_assoc]
    _ = c * 1 := by rw [hab]
    _ = c := by simp
