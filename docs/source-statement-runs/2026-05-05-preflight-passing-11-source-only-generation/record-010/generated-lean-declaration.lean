theorem card_perm (X : Type*) [Fintype X] : Fintype.card (Equiv.Perm X) = (Fintype.card X)! :=
  Fintype.card_perm
