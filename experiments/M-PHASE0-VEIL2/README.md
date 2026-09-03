# M-PHASE0-VEIL2

Commissioned phase-0 acceptance instrument for proposal claim A2: the
depth-aware pyramid base band. This is not a lens-scatter experiment; see
`PREREGISTRATION.md`. The committed verdict is **NOT ROBUST**: the normalized
claw statistic is `-0.0812 [-0.2359, 0.0511]`, but its layer separation and
three other registered potency gates fail, so it is not a licensed KILL.

Run from the repository root with UTF-8 and sibling imports enabled:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = (Get-Location).Path
python experiments\M-PHASE0-VEIL2\src\commission.py
python experiments\M-PHASE0-VEIL2\src\render.py --plan experiments\M-PHASE0-VEIL2\render-plan.json
python experiments\M-PHASE0-VEIL2\src\measure.py
python experiments\M-PHASE0-VEIL2\src\check.py
```

`out/renders`, `out/warpmaps`, `out/run-logs`, and native contact sheets are
reproducible and intentionally ignored. `out/run-records/*.json` records every
render's hash, byte count, full invocation, environment, and banner.
`out/measurement.json` is the complete numerical record; `out/check.json`
records the commissioned cross-checker's result.
