theorem binom_succ_succ {R : Type*} [CommRing R] [BinomialRing R] [NatPowAssoc R] (r : R) (k : ℕ) : Ring.choose (r + 1) (k + 1) = Ring.choose r k + Ring.choose r (k + 1) :=
  Ring.choose_succ_succ r k
