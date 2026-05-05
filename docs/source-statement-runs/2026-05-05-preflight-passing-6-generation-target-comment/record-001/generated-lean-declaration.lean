theorem sum_lim_eq_tsum (f : ℕ → PowerSeries K) (h : Summable f) : HasSum f (∑' n, f n) :=
  hasSum_tsum h
