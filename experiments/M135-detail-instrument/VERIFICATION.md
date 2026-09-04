# M135 independent verification

Status: **VERIFIED — final pass reports no defects**

Read-only `ultracode:ultra-verifier` passes independently inspected the M135
report, source, freeze history, generated artifacts, and D8 adjudication.

The original verification:

- reran all 22 frozen estimator gates;
- reproduced postfilter invariance at machine precision;
- exercised all missing-lineage paths;
- confirmed all 32 permutation maps were distinct derangements;
- checked the freeze commits were path-scoped;
- checked the historical and current FRC rulings;
- compared `RESULTS.md` with `commission.json`; and
- sampled more than 15 verbatim quotations and every citation range.

The D8 update verification independently:

- matched all four historical source blobs;
- reproduced blur `0.9938215871-0.9973982082`, normalized-SNR movement
  `0.537785071%`, RMS-gradient gain `8.2513656688x`, and the power identity;
- reproduced common-filter scaling/invariance to at worst `3.553e-15`;
- confirmed the failed historical null, common-mode FRC `0.972099`, phase-0
  `STOP_REMOVE_RUST` verdict, SPLIT2's held-out tuner-leakage RED, and its
  second-repeat geometry failure;
- regenerated `d8-audit.json` and `audit.json` byte-for-byte in memory; and
- confirmed all 87 citation tokens and 104 individual ranges are valid.

The D8 verifier passes found and caused correction of several audit defects:
a citation checker that ignored second comma-separated ranges; one range
extending three lines past EOF; wording that overstated exact cancellation and
bounded residuals for finite Hann/ring aggregates; a no-result check that
covered only one SPLIT2 output path; and wording that wrongly credited repeated
brackets with temporal-noise independence already present in the odd/even
split. The final verifier reported **PASS with no remaining defects**.

This verifies the mathematical and synthetic estimator work. It does not
replace physical reference/extraction commissioning or produce an M1 score.
