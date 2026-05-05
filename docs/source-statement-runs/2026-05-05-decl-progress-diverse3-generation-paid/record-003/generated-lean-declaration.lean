theorem laurentPoly_unity_and_invertible : (1 : LaurentPoly K) = T 0 ∧ IsUnit (T 1 : LaurentPoly K) := by
  constructor
  · exact laurentPolynomial_one_eq_T_zero
  · exact T_isUnit
