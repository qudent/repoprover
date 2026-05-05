theorem binom_sym {R : Type*} [CommRing R] [BinomialRing R] [NatPowAssoc R] (n : ℕ) (k : ℕ) (h : k ≤ n) : Ring.choose (n : R) k = Ring.choose (n : R) (n - k) := by
  induction' n with n ih generalizing k
  · have hk : k = 0 := Nat.eq_zero_of_le_zero h
    subst hk
    simp [Ring.choose_zero_right]
  · have hn1 : (n.succ : ℕ) = n.succ := rfl
    rcases Nat.eq_zero_or_pos k with (rfl | hkpos)
    · rw [Nat.sub_zero]
      have hself : Ring.choose (n.succ : R) (n.succ : ℕ) = 1 := by
        induction' n.succ with m ihself
        · exact Ring.choose_zero_right 0
        · rw [show (m.succ : R) = (m : R) + 1 by ring,
            Ring.choose_succ_succ (m : R) m,
            ihself,
            Ring.choose_succ_self (m : R)]
          rfl
      exact hself
    · by_cases hkn : k = n.succ
      · subst hkn
        rw [Nat.sub_self, Ring.choose_zero_right]
        exact ?_ -- need a lemma
        sorry
      · have hk_lt : k < n.succ := lt_of_le_of_ne h hkn
        have hk_le_n : k ≤ n := Nat.le_of_lt_succ hk_lt
        have hpos_n_sub_k : 0 < n.succ - k := Nat.sub_pos_of_lt hk_lt
        have h_choose_succ : Ring.choose (n.succ : R) k = Ring.choose (n : R) (k - 1) + Ring.choose (n : R) k := by
          have : k = (k - 1).succ := by omega
          rw [this, Ring.choose_succ_succ (n : R) (k - 1)]
          simp
        have h_choose_sub_succ : Ring.choose (n.succ : R) (n.succ - k) = Ring.choose (n : R) ((n.succ - k) - 1) + Ring.choose (n : R) (n.succ - k) := by
          have h : n.succ - k = ((n - k) : ℕ).succ := by omega
          rw [h, Ring.choose_succ_succ (n : R) (n - k)]
          simp
        rw [h_choose_succ, h_choose_sub_succ]
        have h_sym_n_k : Ring.choose (n : R) k = Ring.choose (n : R) (n - k) := ih k hk_le_n
        rw [h_sym_n_k]
        have h_sub_simp : (n.succ - k) - 1 = n - k := by omega
        rw [h_sub_simp]
        have hk1_le_n : k - 1 ≤ n := by omega
        have h_sym_n_k1 : Ring.choose (n : R) (k - 1) = Ring.choose (n : R) (n - (k - 1)) := ih (k - 1) hk1_le_n
        have h_sub_eq : n - (k - 1) = n.succ - k := by omega
        rw [h_sym_n_k1, h_sub_eq]
        rfl
