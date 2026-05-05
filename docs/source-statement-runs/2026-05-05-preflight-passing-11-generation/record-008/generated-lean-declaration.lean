theorem lem_fps_xa (f : R⟦X⟧) : X * f = PowerSeries.mk (fun n => if n = 0 then 0 else coeff (n - 1) f) := by
  ext n
  simp [coeff_X_mul, coeff_mk]
