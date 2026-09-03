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

## 2026-09-02 re-scope audit

The later claim that A2 was already answered was audited under the frozen
fail-closed gates in `RESCOPE-AUDIT-PLAN.md`. Result:
**`STOP_DO_NOT_BUILD` (0/7 gates passed)**. The predecessor commissioned a
focus-curve classifier, not the base/coarse causal claim; its real artifacts
are no longer present, the result changes sign under positive monotone
per-image scaling, and comparable defocus/diffraction exclusions are absent.
The triage commit also predates this lane's repaired `NOT ROBUST` record.

```powershell
python experiments\M-PHASE0-VEIL2\src\rescope_audit.py
python experiments\M-PHASE0-VEIL2\src\check_rescope_audit.py
```

`out/rescope-audit.json` is the machine-readable evidence ledger.
`out/rescope-audit-check.json` records the independent checker, four positive
controls, and twenty RED self-plants. Per the re-scope order, the failed Part
1 audit prohibited Part 2; no Rust feature was built.
