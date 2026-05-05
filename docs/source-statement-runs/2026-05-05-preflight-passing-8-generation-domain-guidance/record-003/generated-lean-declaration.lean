theorem comp_y_coeff (f g : ℕ → PowerSeries R) (h : embedUnivInBiv f = embedUnivInBiv g) : f = g := by
  ext k
  apply PowerSeries.ext
  intro n
  simpa [coeff_embedUnivInBiv] using congrArg (fun s => s (Finsupp.single 0 n + Finsupp.single 1 k)) h
