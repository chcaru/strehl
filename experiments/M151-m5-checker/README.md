# M151 M5 checker

This lane freezes, implements, and commissions the M5 depth-of-field coverage
checker. The normative definitions are
[`frozen-definitions.json`](frozen-definitions.json); their prose record and
results are in
[`../../docs/research/M151-m5-checker.md`](../../docs/research/M151-m5-checker.md).

## Separation contract

`checker.py manifest` accepts only prepared common-input spectra. It has no
candidate/output argument. `checker.py score` is a separate phase and refuses
a manifest whose content hash or frozen-definition hash has changed.

The prepared NPZ protocol contains:

- `election_crosspower`: `[site,node,16]` adjacent-frame real cross-power in
  `0.05-0.12 cyc/native px`;
- `evaluation_crosspower`: the same in `0.15-0.25 cyc/native px`;
- `source_eval_real` / `source_eval_imag`: source spectra for output scoring;
- stable site identifiers and frozen input coordinates.

The scored-session adapter must produce those arrays from the hashed common
linear ProPhoto inputs and independently reconstructed geometry. The RAW
reader in `commission.py` is deliberately only a lightweight green-channel
development proxy; it is not the scored common-input converter.

## Reproduce

From the repository root:

```powershell
python experiments/M151-m5-checker/checker.py self-test
python experiments/M151-m5-checker/test_checker.py
python experiments/M151-m5-checker/commission.py --refresh
python experiments/M151-m5-checker/verify_results.py
```

The full commissioning command is serial (`OMP_NUM_THREADS`,
`OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, and `NUMEXPR_NUM_THREADS` are forced
to `1`). It reads only the explicitly development/burned RAW paths and writes
only beneath this directory. Prepared spectra and detailed rows are cached in
`out/`; the compact, committed result is `commission-results.json`.
Commissioning intentionally exits 1 while the two real-input eligibility
controls remain red. `verify_results.py` exits 0 only when that partial verdict
and every measured magnitude reproduce exactly.

For direct two-phase use:

```powershell
python experiments/M151-m5-checker/checker.py manifest `
  --prepared <prepared-input.npz> --capture-id <id> --output <manifest.json>

python experiments/M151-m5-checker/checker.py score `
  --prepared <prepared-input.npz> --manifest <manifest.json> `
  --candidate <candidate.npz> --candidate-id <id> --output <result.json>

python experiments/M151-m5-checker/checker.py aggregate `
  --scores <score-a.json> <score-b.json> --output <aggregate.json>
```

The candidate NPZ carries `candidate_real`, `candidate_imag`,
`reference_valid`, and `output_valid`. Validity masks must come from the
independent geometry harness, never from candidate pixel values.
