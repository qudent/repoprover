theorem eq_fps_mulvar_exa1_res1 (k : ℕ) : (PowerSeries.X : PowerSeries ℚ) ^ k * (1 - PowerSeries.X)⁻¹ ^ (k + 1) = PowerSeries.mk (fun n => (n.choose k : ℚ)) :=
  X_pow_mul_inv_one_sub_pow_eq_mk_choose k
