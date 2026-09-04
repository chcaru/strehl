# M169 — M3 occlusion-veil execution

This lane re-runs the frozen M161 v2 commissioning and performs a fail-closed
score preflight. It does not alter the ratified `0.05` bar, open any ARW
pixels, fabricate a product package, or report wall-clock timing.

Run from the repository root, in order:

```powershell
python experiments\M169-m3-veil\capture_feasibility.py
python experiments\M169-m3-veil\test_m3_checker_v2.py
python experiments\M169-m3-veil\full_commission.py
python experiments\M169-m3-veil\anchored_controls.py
python experiments\M169-m3-veil\reproduce_m161_failure.py
python experiments\M169-m3-veil\measurement_preflight.py
python experiments\M169-m3-veil\verify_artifacts.py
```

The feasibility check and unit tests must exit `0`. In the measured M169 run,
the full frozen commissioning exits `3` because its registered improvement arm
does not pass the unchanged median-`h_e` gate. The narrower line-anchored
controls and untouched-M161 reproduction exit `0`, and the final preflight
exits `5` with
`NOT_ADMITTED_COMMISSIONING_FAILED`. If full commissioning is repaired by a
newly authorized instrument version, the preflight will still exit `4` while
any required common-input/product package or M1-qualified comparator envelope
is absent.

`fixtures/control-template.json` represents an eligible edge whose
output-minus-reference residual is identically flat zero. The defect and
improvement controls replace exact, unique full lines in an in-memory copy.
Zero or multiple matches hard-error. A literal constant/no-edge field is
outside M3's registered population and is separately shown to fail closed as
`nonpositive_source_step`; it is not relabelled as a clean score.

The frozen checker and definition are byte-identical copies of M161 commit
`47d67a9f`. `full_commission.py` changes only the obsolete host-reservation
gate and records the current orchestrator policy; its numerical battery is
unchanged.

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
