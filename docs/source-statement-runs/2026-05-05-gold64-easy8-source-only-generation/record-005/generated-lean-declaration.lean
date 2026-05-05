theorem xneq_multiple_iff (R : Type*) [CommRing R] (n : ℕ) (f g : R⟦X⟧) : (f ≡[x^n] g) ↔ ∃ q : R⟦X⟧, f - g = q * X ^ (n+1) := by
  constructor
  · intro h
    have hcoeff (m : ℕ) (hm : m ≤ n) : coeff m f = coeff m g := h m hm
    have hzero (m : ℕ) (hm : m ≤ n) : coeff m (f - g) = 0 := by
      rw [coeff_sub, hcoeff m hm, sub_self]
    let q : R⟦X⟧ := PowerSeries.mk λ k => coeff (k + n + 1) (f - g)
    have hq_coeff (k : ℕ) : coeff k q = coeff (k + n + 1) (f - g) := by
      simp [q, PowerSeries.coeff_mk]
    refine ⟨q, ?_⟩
    ext m
    have hcoeff_prod : coeff m (q * X ^ (n+1)) = (if n+1 ≤ m then coeff (m - (n+1)) q else 0) := by
      by_cases hm : n+1 ≤ m
      · have hsum : coeff m (q * X ^ (n+1)) = coeff (m - (n+1)) q := by
          rw [coeff_mul, coeff_X_pow]
          have hfilter : Finset.filter (λ (x : ℕ × ℕ) => x.2 = n+1) (Finset.antidiagonal m) = {(m - (n+1), n+1)} := by
            ext ⟨i, j⟩
            constructor
            · intro h
              rcases Finset.mem_filter.1 h with ⟨hij, hj⟩
              rw [Finset.mem_antidiagonal] at hij
              have hi : i = m - (n+1) := by omega
              subst hi; subst hj; simp
            · intro h
              rcases Finset.mem_singleton.1 h with ⟨hi, hj⟩
              subst hi; subst hj
              apply Finset.mem_filter.mpr
              constructor
              · apply Finset.mem_antidiagonal.mpr; omega
              · rfl
          rw [hfilter, Finset.sum_singleton]
        rw [hsum, if_pos hm]
      · have hm' : m < n+1 := by omega
        have hzero' : coeff m (q * X ^ (n+1)) = 0 := by
          rw [coeff_mul, coeff_X_pow, Finset.sum_eq_zero]
          intro p hp
          rcases Finset.mem_antidiagonal.1 hp with ⟨hp1, hp2⟩
          have : p.2 ≠ n+1 := by
            intro h
            have : m = p.1 + (n+1) := by omega
            omega
          simp [this]
        rw [hzero', if_neg (by omega : ¬ n+1 ≤ m)]
    rw [hcoeff_prod, coeff_sub]
    by_cases hm : n+1 ≤ m
    · rw [if_pos hm, hq_coeff (m - (n+1)), Nat.sub_add_cancel hm]
    · have hm' : m ≤ n := by omega
      rw [if_neg (by omega : ¬ n+1 ≤ m), hzero m hm']
  · intro h
    rcases h with ⟨q, hq⟩
    intro m hm
    have hcoeff_sub : ∀ m, coeff m (f - g) = coeff m (q * X ^ (n+1)) := by
      intro m; rw [hq]
    have hcoeff_prod_zero (hm : m ≤ n) : coeff m (q * X ^ (n+1)) = 0 := by
      rw [coeff_mul, coeff_X_pow, Finset.sum_eq_zero]
      intro p hp
      rcases Finset.mem_antidiagonal.1 hp with ⟨hp1, hp2⟩
      have : p.2 ≠ n+1 := by
        intro h
        have : m = p.1 + (n+1) := by omega
        omega
      simp [this]
    have hzero' : coeff m (f - g) = 0 := by
      rw [hcoeff_sub m, hcoeff_prod_zero hm]
    rw [coeff_sub] at hzero'
    exact sub_eq_zero.mp hzero'
