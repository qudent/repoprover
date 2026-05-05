theorem coeff_finitely_determined_iff (a : I → PowerSeries R) (n : ℕ) :
  (CoeffFinitelyDeterminedInSum a n ↔ ∃ M : Finset I, DeterminesCoeffInSum a M n) ∧
  (CoeffFinitelyDeterminedInProd a n ↔ ∃ M : Finset I, DeterminesCoeffInProd a M n) :=
by
  constructor <;> rfl
