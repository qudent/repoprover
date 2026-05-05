theorem binom_rec {R : Type*} [CommRing R] [BinomialRing R] [NatPowAssoc R]
    (m : R) (n : ℕ) (hn : 0 < n) :
    Ring.choose m n = Ring.choose (m - 1) (n - 1) + Ring.choose (m - 1) n := by
  have h : m = (m - 1) + 1 := by ring
  have hn' := Nat.succ_pred_eq_of_pos hn
  conv_lhs => rw [h, ← hn', Nat.pred_eq_sub_one]
  rw [Ring.choose_succ_succ (m - 1) (n - 1)]
  simp only [Nat.sub_add_cancel hn]
