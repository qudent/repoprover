theorem partition_weakly_decreasing_finite {n : ℕ} (p : Nat.Partition n) : Antitone p.parts ∧ (∀ᶠ i in Filter.cofinite, p.parts i = 0) := by
  exact ⟨p.parts_anti, p.parts_finite⟩
