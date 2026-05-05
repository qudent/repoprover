lemma pow_eq_iterate {X : Type*} (α : Equiv X X) (i : ℕ) : (α ^ i : X → X) = α^[i] := by
  induction i with
  | zero => simp
  | succ i ih => simp [pow_succ, Function.iterate_succ', mul_apply, ih]
