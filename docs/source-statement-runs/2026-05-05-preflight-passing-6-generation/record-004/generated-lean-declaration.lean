lemma binom_rec (m n : ℕ) : Nat.choose (m+1) (n+1) = Nat.choose m n + Nat.choose m (n+1) :=
  Nat.choose_succ_succ m n
