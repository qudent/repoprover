theorem binom_rec {R : Type*} [CommRing R] [BinomialRing R] [NatPowAssoc R] (r : R) (k : ℕ) :
    Ring.choose (r + 1) (k + 1) = Ring.choose r k + Ring.choose r (k + 1) := by
  have hk : 0 < k + 1 := Nat.succ_pos k
  have h := pascal_identity_ring (r + 1) (k + 1) hk
  have hsub1 : (r + 1) - 1 = r := by ring
  have hsub2 : ((k + 1 : ℕ) - 1) = k := by simp
  simpa [hsub1, hsub2] using h
