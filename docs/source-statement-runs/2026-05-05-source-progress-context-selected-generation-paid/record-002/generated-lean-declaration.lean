theorem alternant_swap (α : Fin N → ℕ) (i j : Fin N) (hij : i ≠ j) : alternant N (α ∘ Equiv.swap i j) = - alternant N α := by
  set s := Equiv.swap i j with hs
  have h_sign : Equiv.Perm.sign s = -1 := Equiv.Perm.sign_swap hij
  unfold alternant
  simp only [Function.comp_assoc, hs]
  calc
    (∑ τ : Equiv.Perm (Fin N), Equiv.Perm.sign τ • xPow (α ∘ (s ∘ τ))) = 
        (∑ τ : Equiv.Perm (Fin N), Equiv.Perm.sign (s * τ) • xPow (α ∘ τ)) := by
      apply Finset.sum_bij (fun τ _ => s * τ) (by simp) (by
        intro τ₁ τ₂ _ _ h
        apply mul_left_cancel s
        exact h
      ) (by
        intro τ _
        simp [s, Function.comp, Equiv.Perm.sign_mul, Equiv.swap_mul_self, mul_assoc]
      ) (by
        intro τ _
        refine ⟨s * τ, by simp, ?_⟩
        simp [s]
      )
    _ = (∑ τ : Equiv.Perm (Fin N), (Equiv.Perm.sign s * Equiv.Perm.sign τ) • xPow (α ∘ τ)) := by
      simp [Equiv.Perm.sign_mul]
    _ = Equiv.Perm.sign s • (∑ τ : Equiv.Perm (Fin N), Equiv.Perm.sign τ • xPow (α ∘ τ)) := by
      simp [Finset.smul_sum, smul_smul]
    _ = (-1) • (∑ τ : Equiv.Perm (Fin N), Equiv.Perm.sign τ • xPow (α ∘ τ)) := by rw [h_sign]
    _ = - (∑ τ : Equiv.Perm (Fin N), Equiv.Perm.sign τ • xPow (α ∘ τ)) := by simp
