theorem isInverse_unique {a b c : L} (h1 : IsInverse a b) (h2 : IsInverse a c) : b = c :=
  AlgebraicCombinatorics.DividingFPS.inverse_unique h1 h2
