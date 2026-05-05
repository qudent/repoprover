lemma pow_eq_iterate (X : Type*) (α : Equiv.Perm X) (i : ℕ) : (α ^ i : X → X) = α^[i] := by
  induction i with
  | zero => ext x; simp
  | succ n ih =>
    ext x
    rw [pow_succ, Equiv.Perm.mul_apply, ih, Function.iterate_succ']
