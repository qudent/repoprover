lemma pow_eq_iterate {X : Type*} (α : Equiv X X) (i : ℕ) : (α ^ i).toFun = α^[i] := by
  induction i with
  | zero =>
    simp
  | succ i ih =>
    ext x
    rw [pow_succ, Equiv.mul_apply, ih, Function.iterate_succ']
    rfl
