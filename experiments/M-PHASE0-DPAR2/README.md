# M-PHASE0-DPAR2

Injection/recovery calibration for M6's C4c/DPAR null.  The plant uses the
independently measured nonlinear breathing track from M103, not a linear
`g_k`.  Read `PREREGISTRATION.md` before the result.

The capture trees and the M6/M103 lanes are read-only.  Generated files are
small JSON records under this lane's `out/`.

```powershell
cd C:\dev\blog\death-of-software\projects\strehl
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=(Get-Location).Path

python experiments\M-PHASE0-DPAR2\src\commission.py
python experiments\M-PHASE0-DPAR2\src\measure.py
```

`commission.py` must pass before `measure.py` will run.  The primary result is
conditional randomisation power over all 96 torus phases of M6 `119MSDCF`.
`109MSDCF` and `coffee-bean` are preregistered secondary replications.

| path | purpose |
|---|---|
| `src/fixed_oracle.py` | literal cancellation-immune C3 input and answer; imports no estimator |
| `src/dpar2lib.py` | curved physical plant, exact fast S2 evaluation, MDA bootstrap |
| `src/commission.py` | fixed M103 predicate, M6 estimator-read controls, wiring/null checks |
| `src/measure.py` | registered ladder, MDA80, and verdict |
| `out/commission.json` | complete control readings and source hashes |
| `out/measurement.json` | all 96-phase dose results, uncertainty, and verdict |

No Rust source is used or changed.  The estimator is imported unchanged from
`experiments/m6-residual-halo/m6_lib.py`; C6 compares the accelerated evaluation
against that exact function on three fixed phase/dose cases.
