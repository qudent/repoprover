theorem lem_fps_xa (a : R⟦X⟧) : X * a = PowerSeries.mk (fun n => if n = 0 then 0 else coeff (n - 1) a) := by
  ext n
  rw [coeff_X_mul, coeff_mk]
