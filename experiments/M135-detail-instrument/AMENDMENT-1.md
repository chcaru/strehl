# M135 commissioning amendment 1

Status: **FROZEN BEFORE REPLACEMENT OUTCOME GENERATION**

The first execution produced `commission-run1-invalid.json`. Inspection found
that `commission.py` executed C14 and C15 once each even though the frozen
preregistration requires `NO_DETAIL` in **128/128** independently generated
flat and repeated-template populations.

That is an implementation/protocol mismatch. The first run is retained and
labelled invalid; none of its gates is admitted as commissioning evidence.

This amendment changes only the C14/C15 repetition loop and result schema:

- generate 128 independent flat populations;
- generate 128 independent repeated-template populations;
- retain status counts and the first diagnostic from each;
- require exactly 128 `NO_DETAIL` statuses in each arm.

No seed, synthetic distribution, candidate computation, challenge effect,
threshold, or other gate changes. The replacement run may begin only after
this amendment and the corrected source are committed.
