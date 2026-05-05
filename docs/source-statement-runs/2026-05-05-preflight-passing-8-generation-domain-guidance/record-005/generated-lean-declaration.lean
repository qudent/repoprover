theorem lem_fps_xa (f : R⟦X⟧) : X * f = PowerSeries.mk (fun n => if n = 0 then 0 else coeff (n - 1) f) :=
  X_mul_eq_shift f
