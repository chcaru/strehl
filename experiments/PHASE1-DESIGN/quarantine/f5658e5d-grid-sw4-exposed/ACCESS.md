# Quarantined W1 attempt — grid-1 sw4 consumed

This directory preserves the superseded W1 run based on design commit
`f5658e5d`. It is not input to the revised `fe111781` W1.

Before the leakage halt arrived, candidate outcomes from
`D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw4-cpl`
became visible:

- all 55 RAWs were decoded and aligned;
- one reference-frame preview was inspected to site the old crops;
- candidate and legacy `n_eff` widths were scored for all seven bands, both
  old ROIs, and all 161 values `k=0.00,0.05,...,8.00`;
- detail and flat-power candidate/legacy ratios at the old preregistered
  negative-report sentinel `k=0.00` were computed and observed.

Therefore **grid-1 sw4 is consumed development data and may not remain an
untouched W5/SOTA-scorecard holdout for this version**. No other calibration
grid was decoded or scored by W1.

The original tracked history is:

- `e64fca59e86154284d81903dca0a5622876aa9a8` — old preregistration;
- `4bada8e3cfabe96fb45f7836bfd620606471dfd8` — Windows hash-key fix;
- `6b9eb171483e7bc6c017453616c264961a1c931c` — exposed old outcomes.

The files beside this note are retained only as an audit trail. Revised W1
programs must refuse to read them.
