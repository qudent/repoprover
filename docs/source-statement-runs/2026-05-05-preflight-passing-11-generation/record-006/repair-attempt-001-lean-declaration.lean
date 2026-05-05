theorem binom_symm (n k : ℕ) (hk : k ≤ n) : Nat.choose n k = Nat.choose n (n - k) := (Nat.choose_symm hk).symm
