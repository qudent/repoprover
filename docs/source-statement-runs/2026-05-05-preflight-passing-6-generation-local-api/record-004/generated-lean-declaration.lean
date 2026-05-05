theorem binom_rec (m n : ℕ) (hn : 0 < n) (hm : 0 < m) : m.choose n = (m - 1).choose (n - 1) + (m - 1).choose n :=
  pascal_identity m n hn hm
