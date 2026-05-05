theorem thm_commring_inverse_uni {L : Type*} [CommRing L] {a b c : L} (hb : a * b = 1) (hc : a * c = 1) : b = c :=
  inverse_unique hb hc
