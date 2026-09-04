# M169 — M3 occlusion-veil execution

This lane preserves the historical M161 v2 commissioning result, commissions
the frozen checker under M169 registration v3, and performs a fail-closed score
preflight. It does not alter the ratified `0.05` bar, open any ARW pixels,
fabricate a product package, or report wall-clock timing.

M169 commissioning registration v3 applies M174's independently adjudicated
assertion correction from commit `a9176fef`: the unchanged 0.5%-each boundary
reduction must improve both channels by at least five percentage points and
must fail only median `h_e`. A separate 0.25%-each green recovery arm must pass
every gate. Its magnitude is registered from geometry, not the observed
crossing: two overlapping components sum to 0.5%, exactly half of the
unchanged 1% median gate.

Run from the repository root, in order:

```powershell
python experiments\M169-m3-veil\capture_feasibility.py
python experiments\M169-m3-veil\test_m3_checker_v2.py
python experiments\M169-m3-veil\full_commission.py
python experiments\M169-m3-veil\anchored_controls.py
python experiments\M169-m3-veil\reproduce_m161_failure.py
python experiments\M169-m3-veil\characterize_improvement_curve.py
python experiments\M169-m3-veil\measurement_preflight.py
python experiments\M169-m3-veil\verify_artifacts.py
```

The feasibility check, unit tests and corrected v3 battery exit `0`. The
untouched-M161 reproduction remains a historical proof that v2 failed its
mis-registered whole-arm-pass assertion. The final preflight exits `4` with
`UNMEASURED_COMPARATOR_QUALIFICATION`: a commissioned instrument is not an M3
score or axis pass, and scorecard blockers `(a)`, `(b)` and `(d)` remain.

`characterize_improvement_curve.py` imports the hash-verified untouched M161
source and measures the combined rim-and-veil transfer from zero through 6%.
It does not replace the registered 0.5% arm, change any gate or assertion, or
open product pixels. It records the fixed-seed median-`h_e` crossing bracket in
`out/improvement-response-curve.json`.

`fixtures/control-template.json` represents an eligible edge whose
output-minus-reference residual is identically flat zero. The defect and
improvement controls replace exact, unique full lines in an in-memory copy.
Zero or multiple matches hard-error. A literal constant/no-edge field is
outside M3's registered population and is separately shown to fail closed as
`nonpositive_source_step`; it is not relabelled as a clean score.

The frozen checker and definition are byte-identical copies of M161 commit
`47d67a9f`. `full_commission.py` retains M161's numerical checker, plants,
seed and population, removes the obsolete host-reservation gate, applies the
M174-authorized assertion-only correction, and adds the separately registered
design-derived green recovery arm.

Prior-art search before commissioning named:

- `docs/research/M87-occlusion.md`;
- `docs/research/M36-VERIFICATION.md`;
- `docs/research/ORCH-veiling.md`;
- `docs/research/M63-bimodality.md`;
- `docs/research/M161-m3-ratification.md`;
- `docs/research/M35-fit-generality-measured.md`;
- `docs/research/M25-simulator-measured.md`;
- `docs/research/M31-VERIFICATION.md`;
- `docs/research/M152-site-census.md`;
- `docs/research/M79-edof-microscopy-survey.md`;
- `docs/research/M133-blocker-audit.md`;
- `docs/research/BUILD-HALO.md`;
- `docs/research/M146-unlock-audit.md`;
- `docs/research/M39-verify-detail-metric.md`;
- `docs/research/V-veiling.md`; and
- `docs/research/M151-m5-checker.md`.
