theorem lem_fps_xa (f : R⟦X⟧) (k : ℕ) (n : ℕ) : coeff n (f * X ^ k) = if n < k then 0 else coeff (n - k) f := by
  rw [mul_comm, coeff_X_pow_mul]
