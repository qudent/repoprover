theorem sum_lim_eq_tsum (f : ℕ → PowerSeries K) (h : CoeffStabilizesTo f (∑' n, f n)) : CoeffStabilizesTo (fun i => ∑ n in Finset.range (i+1), f n) (∑' n, f n) := by
  intro n
  obtain ⟨J, hJ⟩ := h n
  use J
  intro i hi
  have hcoeff : coeff K n (∑' n, f n) = coeff K n (∑ n in Finset.range (i+1), f n) := by
    calc
      coeff K n (∑' n, f n) = coeff K n (f n) := by
        sorry
      _ = coeff K n (∑ n in Finset.range (i+1), f n) := by
        sorry
  exact hcoeff
