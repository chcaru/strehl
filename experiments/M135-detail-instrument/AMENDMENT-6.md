# M135 commissioning amendment 6

Status: **FROZEN BEFORE SHAPE-GUARD RE-RUN**

The first successful amendment-4/5 run passed all 25 gates. A subsequent
fail-closed API review found that an invalid primary array shape could reach
the flat power-ratio diagnostic after `_status` had already classified it,
potentially raising an indexing error instead of returning `INVALID_SHAPE`.

This amendment changes only that refusal path. Flat/detail power ratios are
computed only when both four-array bundles are finite, internally
shape-consistent, have sixteen cells, and have identical shapes. Otherwise the
ratios are `null` and the already determined typed primary refusal is returned.
No valid-input statistic, challenge transform, threshold, or gate changes.
The successful amendment-5 artifact is retained, and the replacement must
reproduce it byte-for-byte.
