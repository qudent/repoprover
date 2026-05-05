open Filter
open scoped Topology

theorem partial_sums_tendsto_tsum (f : ℕ → PowerSeries K) [TopologicalRing K] (hsum : Summable f) :
    Tendsto (fun i : ℕ => ∑ n in range (i+1), f n) atTop (𝓝 (∑' n, f n)) :=
  hsum.hasSum.tendsto_sum_nat.comp (tendsto_add_atTop_nat 1)
