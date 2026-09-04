# M135 commissioning amendment 3

Status: **FROZEN BEFORE REPLACEMENT OUTCOME GENERATION**

The third execution produced `commission-run3-superseded.json` and passed
amendment 2. A fail-closed API audit then found that `CaptureSet` defaulted
missing target lineage and calibration evidence to admissible values. That
made omission equivalent to proof, contrary to the certificate design.

This amendment changes no numeric bar or estimand. It tightens provenance:

1. clipping fraction, effective bit depth, calibration-residual correlation,
   and target lineage are mandatory;
2. omission returns `MISSING_LINEAGE`, never a number;
3. synthetic eligible captures set all four fields explicitly;
4. C21 requires the missing-lineage refusal;
5. C15's predictable target is now a full-rank public cyclic code rather than
   a constant template;
6. the same predictable code is scored once with a deliberately forged
   nonperiodic lineage. That diagnostic is expected to show that pixels alone
   cannot prove unpredictability, just as the shared-flat diagnostic shows
   that pixels alone cannot prove sensor-pattern independence.

The first run remains invalid. Runs two and three are valid under their then
frozen batteries but are superseded by the stricter fail-closed contract. The
replacement run may begin only after this amendment and source are committed.
