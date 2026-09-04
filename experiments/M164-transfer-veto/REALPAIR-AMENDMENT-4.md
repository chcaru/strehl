# M164 real-pair audit — amendment 4

Status: **FROZEN AFTER RUN 4 FAILED, BEFORE RUN 5**

Run 4 produced valid `NOT_VETOED` results for `113` (`30/40` eligible
sites) and `113-sharp` (`21/40`), but `cb` stopped at fixed site 7 before a
pair verdict. The persistent artifact is `out/realpair-run4-partial.json`,
SHA-256
`9CCB71B796A5B72F4CF20AD3DC9FA230A31215975089409A2D9C3FEF5F6009A8`.

The exception was an evaluation-order defect. Site 7's comparator crop is
constant at `1.0` with rail fraction `1.0`, so the existing
`COMPARATOR_RAIL_FRACTION` gate already makes it ineligible. The runner instead
attempted phase registration before applying that gate, and phase preparation
correctly rejected the constant field as degenerate.

This amendment moves the unchanged comparator rail-fraction gate immediately
after the comparator crop is read, before registration:

1. a comparator crop above the existing `0.001` rail-fraction limit is
   recorded as `COMPARATOR_RAIL_FRACTION` and skipped;
2. all fixed sites continue to be evaluated;
3. the 40 sites, minimum of 8, rail threshold, registration thresholds,
   adapters, transfer families and pair rule remain unchanged; and
4. no `cb` transfer-veto result was observed before this amendment.

This repairs control flow for a pre-existing exclusion; it does not admit a
site that the frozen protocol rejected.
