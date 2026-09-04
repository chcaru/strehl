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

## Amendment 4/5 verification

Status: **VERIFIED by a separate implementation path; not an independent
author**

`flat_verify.py` does not import `commission.py`. It independently:

- checked that `commission.json` passes all 25 gates;
- compared every pre-amendment information, transfer, residual, tone,
  sample-size, permutation, checker, averaging, and C0-C21 result against
  `commission-run4-pre-flat-null.json`;
- verified every uncontaminated arm's maximum flat/detail information,
  reference-repeatability, and output-repeatability ratios against the frozen
  `0.10 / 0.25 / 0.10` bars;
- checked common-artifact rejection in 128/128 populations, structured-flat
  rejection at ratios `1/1/1`, and missing-flat rejection in 128/128;
- checked the four frozen squared noise gains, q95 information ratio below
  `0.90`, and zero promotions;
- read M137's retained JSON directly and matched its detailed gap, flat gap,
  ratio, failed S7 gate, preserved old gates, and final failure; and
- generated a fresh 128-site independent probe. Baseline was `OK`; the
  high-band noise plant reduced `J_TR` from `3.9841138452442353` to
  `2.6334749277223413` (`0.6609938947567657x`); its flat information ratio
  remained `0`; structured and common-artifact flats failed; and omission
  returned `MISSING_FLAT_CONTROL`;
- exercised a malformed primary bundle and confirmed typed `INVALID_SHAPE`
  rather than an indexing error; and
- confirmed amendment 6's replacement campaign is byte-identical to the
  pre-shape-guard artifact.

All 20 checks passed. The machine-readable result is
`flat-verification.json`.
