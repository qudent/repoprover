theorem coeff_finitely_determined_iff (a : I → PowerSeries R) (n : ℕ) :
    (PowerSeries.CoeffFinitelyDeterminedInSum a n ↔ ∃ M : Finset I, PowerSeries.DeterminesCoeffInSum a M n) ∧
    (PowerSeries.CoeffFinitelyDeterminedInProd a n ↔ ∃ M : Finset I, PowerSeries.DeterminesCoeffInProd a M n) :=
by
  constructor <;> rfl
