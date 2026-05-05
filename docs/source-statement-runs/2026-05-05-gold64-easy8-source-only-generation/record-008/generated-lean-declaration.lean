theorem qBinomial_eq_zero_of_gt {R : Type*} [Semiring R] (n k : ℕ) (q : R) (h : k > n) : qBinomial n k q = 0 := by
  have hle : ¬ k ≤ n := by omega
  simp [qBinomial, hle]
