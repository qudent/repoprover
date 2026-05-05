theorem sum_lim (f : ℕ → PowerSeries K) (hsum : Summable f) : CoeffStabilizesTo (fun i => ∑ n in Finset.range (i+1), f n) (tsum f hsum) := by
  intro n
  have hn := hsum n
  rcases hn with ⟨s, hs⟩
  by_cases hne : s.Nonempty
  · let N := s.max' hne
    use N
    intro i hi
    have hiN : N ≤ i := hi
    have hsub : s ⊆ Finset.range (i+1) := by
      intro x hx
      rw [Finset.mem_range]
      have hxN : x ≤ N := Finset.le_max' s x hx
      exact Nat.lt_succ_of_le (Nat.le_trans hxN hiN)
    have hzero_range : ∀ x, x ∈ Finset.range (i+1) → x ∉ s → coeff K n (f x) = 0 := by
      intro x hx hxnot
      by_contra h
      apply hxnot
      exact hs x h
    calc
      coeff K n (∑ j in Finset.range (i+1), f j) = ∑ j in Finset.range (i+1), coeff K n (f j) := by rw [coeff_sum]
      _ = ∑ j in s, coeff K n (f j) := (Finset.sum_subset hsub hzero_range).symm
      _ = coeff K n (tsum f hsum) := by
        dsimp [tsum]
        rw [coeff_mk]
  · use 0
    intro i hi
    have hs_empty : s = ∅ := Finset.not_nonempty_iff_eq_empty.mp hne
    have hzero_all : ∀ x, coeff K n (f x) = 0 := by
      intro x
      by_contra h
      have hx_s : x ∈ s := hs x h
      rw [hs_empty] at hx_s
      exact Finset.not_mem_empty x hx_s
    have hzero_tsum : coeff K n (tsum f hsum) = 0 := by
      dsimp [tsum]
      rw [coeff_mk, hs_empty, Finset.sum_empty]
    calc
      coeff K n (∑ j in Finset.range (i+1), f j) = ∑ j in Finset.range (i+1), coeff K n (f j) := by rw [coeff_sum]
      _ = 0 := by
        simp [hzero_all]
      _ = coeff K n (tsum f hsum) := by rw [hzero_tsum]
where
  Summable (f : ℕ → PowerSeries K) : Prop := ∀ n, ∃ s : Finset ℕ, ∀ i, coeff K n (f i) ≠ 0 → i ∈ s
  tsum (f : ℕ → PowerSeries K) (h : Summable f) : PowerSeries K :=
    PowerSeries.mk (λ n => ∑ i in (Classical.choose (h n)), coeff K n (f i))
