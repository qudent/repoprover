theorem alternant_properties (α : Fin N → ℕ) (i j : Fin N) (hij : i ≠ j) (hα : α i = α j) :
    alternant N α = 0 ∧ alternant N (α ∘ Equiv.swap i j) = - alternant N α :=
by
  have hswap : Equiv.Perm.sign (Equiv.swap i j : Equiv.Perm (Fin N)) = -1 :=
    Equiv.Perm.sign_swap hij
  have hcomp_same : α ∘ Equiv.swap i j = α := by
    ext k
    by_cases hik : k = i
    · subst hik; simp [hα]
    · by_cases hjk : k = j
      · subst hjk; simp [hα]
      · simp [hik, hjk]
  constructor
  · -- part (a): alternant α = 0
    have hsum : (∑ σ : Equiv.Perm (Fin N), Equiv.Perm.sign σ • xPow (α ∘ σ)) = 0 := by
      apply Finset.sum_involution (fun σ _ => Equiv.swap i j * σ) ?_ ?_ ?_ ?_
      · intro σ hσ; exact Finset.mem_univ _
      · intro σ hσ; simp [mul_assoc, Equiv.swap_mul_self]
      · intro σ hσ
        simp [Equiv.Perm.sign_mul, hswap, hcomp_same, Function.comp.assoc, smul_smul]
    simpa [alternant, AlgebraicCombinatorics.alternant] using hsum
  · -- part (b): alternant (α ∘ swap) = - alternant α
    have hsum_b : (∑ σ : Equiv.Perm (Fin N), Equiv.Perm.sign σ • xPow ((α ∘ Equiv.swap i j) ∘ σ)) =
        - (∑ σ : Equiv.Perm (Fin N), Equiv.Perm.sign σ • xPow (α ∘ σ)) := by
      calc
        (∑ σ : Equiv.Perm (Fin N), Equiv.Perm.sign σ • xPow ((α ∘ Equiv.swap i j) ∘ σ)) =
            (∑ σ : Equiv.Perm (Fin N), Equiv.Perm.sign σ • xPow (α ∘ (Equiv.swap i j ∘ σ))) :=
          by simp [Function.comp.assoc]
        _ = (∑ τ : Equiv.Perm (Fin N), Equiv.Perm.sign (Equiv.swap i j * τ) • xPow (α ∘ τ)) := by
          apply Finset.sum_bij (fun τ _ => Equiv.swap i j * τ) ?_ ?_ ?_ ?_ ?_
          · intro τ hτ; exact Finset.mem_univ _
          · intro τ₁ hτ₁ τ₂ hτ₂ h_eq
            apply_fun (fun t => Equiv.swap i j * t) at h_eq
            simpa [mul_assoc, Equiv.swap_mul_self] using h_eq
          · intro σ hσ
            refine ⟨Equiv.swap i j * σ, Finset.mem_univ _, ?_⟩
            simp
          · intro σ hσ; simp
        _ = (∑ τ : Equiv.Perm (Fin N), (- Equiv.Perm.sign τ) • xPow (α ∘ τ)) := by
          simp [hswap, Equiv.Perm.sign_mul]
        _ = - (∑ τ : Equiv.Perm (Fin N), Equiv.Perm.sign τ • xPow (α ∘ τ)) := by
          simp [Finset.sum_neg_distrib, neg_smul]
    simpa [alternant, AlgebraicCombinatorics.alternant] using hsum_b
