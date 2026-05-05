lemma coeffFinitelyDeterminedInSum_iff (a : I → PowerSeries R) (n : ℕ) :
    CoeffFinitelyDeterminedInSum a n ↔ ∃ (M : Finset I), DeterminesCoeffInSum a M n :=
  ⟨fun h => h, fun h => h⟩
