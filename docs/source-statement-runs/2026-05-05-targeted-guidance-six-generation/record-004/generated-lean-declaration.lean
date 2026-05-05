theorem empty_unique (p : Partition 0) : p = empty := by
  rw [eq_iff_parts_eq]
  rw [partition_zero_parts p, partition_zero_parts empty]
