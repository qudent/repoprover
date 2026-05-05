theorem parts_sum_eq_n (n : ℕ) (p : Nat.Partition n) : p.parts.sum = n :=
  p.parts_sum
