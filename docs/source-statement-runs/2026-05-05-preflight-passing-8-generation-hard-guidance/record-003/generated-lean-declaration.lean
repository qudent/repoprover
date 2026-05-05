lemma prop_fps_mulvar_comp_y_coeff {f g : ℕ → PowerSeries R} (h : embedUnivInBiv f = embedUnivInBiv g) : ∀ k, f k = g k := by
  intro k
  ext n
  have hcoeff := congrArg (fun φ : BivFPS R => φ (Finsupp.single 0 n + Finsupp.single 1 k)) h
  simpa [coeff_embedUnivInBiv] using hcoeff
