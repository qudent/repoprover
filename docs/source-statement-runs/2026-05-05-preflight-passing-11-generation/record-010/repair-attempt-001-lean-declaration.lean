lemma pow_eq_iterate {X : Type*} (α : Equiv X X) (i : ℕ) : (α ^ i).toFun = α^[i] := by
  induction i with
  | zero =>
    simp
  | succ i ih =>
    calc
      (α ^ (i + 1)).toFun = ((α ^ i) * α).toFun := by simp [pow_succ]
      _ = (α ^ i).toFun ∘ α.toFun := by ext x; simp
      _ = (α^[i] ∘ α) := by rw [ih]
      _ = α^[i+1] := by simp [Function.iterate_succ']
