lemma card_perm (X : Type*) [Fintype X] [DecidableEq X] : Fintype.card (Equiv.Perm X) = (Fintype.card X)! :=
  Fintype.card_perm
