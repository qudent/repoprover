theorem sum_lim (f : ℕ → PowerSeries K) [TopologicalSpace (PowerSeries K)] [ContinuousAdd (PowerSeries K)] (h : Summable f) : HasSum f (∑' n, f n) :=
  h.hasSum
