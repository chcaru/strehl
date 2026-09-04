# M135 consumer-checker amendment 1

Status: **FROZEN BEFORE REPLACEMENT SELF-TEST**

The first checker self-test passed all fourteen registered controls. A
subsequent fail-closed input review found that Python and NumPy would coerce
JSON Booleans and numeric strings into numbers. A producer could therefore
submit `true` as a ratio of `1.0`, or `"1.0"` as a numeric draw, instead of the
required JSON number.

This amendment changes no threshold, decision rule, valid numeric input, or
physical claim. It requires:

- scalar metric values to be JSON integers or floats, never Booleans;
- bootstrap vectors and matrices to contain only JSON integers or floats,
  never Booleans or strings; and
- site counts, replicate counts, seeds, and capture counts to be JSON integers,
  never Booleans or numeric strings.

The malformed-payload control gains Boolean and numeric-string plants. The
replacement self-test may run only after this amendment and checker change are
committed.
