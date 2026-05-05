theorem binom_sym (n k : ℕ) (hk : k ≤ n) : (Nat.choose n k : ℝ) = (Nat.choose n (n - k) : ℝ) := by
  exact_mod_cast (Nat.choose_symm hk).symm
