# M152 input-only site census

This lane freezes and runs the shared input-only population for scorecard M3
and M4. It never accepts a candidate-output path.

Key artifacts:

- `census-definition.json`: frozen selector and M4 population;
- `out/census-manifest.json`: measured input-only census;
- `out/noise-calibration.json`: non-holdout temporal-band calibration;
- `m3-checker-definition.json`, `m3_checker.py`, and
  `out/m3-commission.json`: historical pooled-mean checker and deliberately
  red commissioning result;
- `side-max-commission-definition.json` and
  `commission_m3_side_max.py`: supplemental commissioning pinned to the
  canonical M161 side-max scorer;
- `out/m3-side-max-commission.json`: preserved freeze-1 red result;
- `out/m3-side-max-commission-v2.json`: commissioned side-max reduction with
  empirical clean-noise tails; and
- `verify_artifacts.py`: fast hashes and recounts.

Run:

```powershell
python experiments\M152-site-census\test_census.py
python experiments\M152-site-census\test_m3_checker.py
python experiments\M152-site-census\test_m3_side_max_commission.py
python experiments\M152-site-census\commission_m3_side_max.py
python experiments\M152-site-census\verify_artifacts.py
```

`commission_m3.py` exits 3 by design because the registered two-sided veil
mean misses the mandatory one-sided far-veil plant. The versioned side-max
commission exits 0: all four empirical clean-noise arms clear the unchanged
bars, and the one-sided plant moves from `0.027243` to `0.054486`. It is
reduction-level commissioning, not an M3 product score. See the research
report for the preserved freeze-1 fixture failure and scope limits.

The local `.gitattributes` pins text artifacts to CRLF because the pre-output
definition and result hashes were frozen on Windows. This makes those hashes
stable on checkouts whose global `core.autocrlf` setting differs.
