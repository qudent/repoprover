/-- The `x^n`-coefficient in the sum of `(a_i)_{i ∈ I}` is finitely determined
if there exists a finite subset `M` that determines it.
(Label: def.fps.xn-coeff-fin-determined part (a)) -/
def CoeffFinitelyDeterminedInSum (a : I → PowerSeries R) (n : ℕ) : Prop :=
  ∃ M : Finset I, DeterminesCoeffInSum a M n
