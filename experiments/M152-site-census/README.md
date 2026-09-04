# M152 input-only site census

This lane freezes and runs the shared input-only population for scorecard M3
and M4. It never accepts a candidate-output path.

Key artifacts:

- `census-definition.json`: frozen selector and M4 population;
- `out/census-manifest.json`: measured input-only census;
- `out/noise-calibration.json`: non-holdout temporal-band calibration;
- `m3-checker-definition.json` and `m3_checker.py`: M3 scoring core;
- `out/m3-commission.json`: deliberately red M3 commissioning result; and
- `verify_artifacts.py`: fast hashes and recounts.

Run:

```powershell
python experiments\M152-site-census\test_census.py
python experiments\M152-site-census\test_m3_checker.py
python experiments\M152-site-census\verify_artifacts.py
```

`commission_m3.py` exits 3 by design because the registered two-sided veil
mean misses the mandatory one-sided far-veil plant. See
`docs/research/M152-site-census.md`.

The local `.gitattributes` pins text artifacts to CRLF because the pre-output
definition and result hashes were frozen on Windows. This makes those hashes
stable on checkouts whose global `core.autocrlf` setting differs.
