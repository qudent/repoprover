theorem sum_lim (f : ℕ → PowerSeries K) (h : Summable f) : HasSum f (∑' n, f n) :=
  h.hasSum
