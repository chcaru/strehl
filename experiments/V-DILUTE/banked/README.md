# Banked V-DILUTE measurement records

These 38 text/JSON files are the machine-readable residue of this lane's
measurements. The heavy scratch that produced them
(`D:\strehl-out\V-DILUTE\`, 3.36 GB of TIFFs) has been deleted to reclaim
disk. **These files are banked here because some of them cannot be
regenerated at any price.**

## `arms_*.json` — 10 files, the premium/sharpness arm ladder

Written by `vd_prem_run.py`. Each holds, per arm, the premium figure and the
noise-corrected sharpness ratios in four bands, for one subject and one twin
seed. These are the numbers behind the ranked-arm table in Addendum H of
`docs/research/V-DILUTE.md`.

**IRREPLACEABLE.** Their inputs — `112MSDCF.npz` and `119MSDCF.npz` under
`C:\dev\strehl-out\V-NEVERWORSE\bundle\` — were deleted at 22:48 on 27 Aug by
another lane's cleanup, with no copy on either drive. `vd_prem_run.py` cannot
be re-run against them without first rebuilding the aligned bundles from the
read-only originals in `D:\personal\macro\` via `vn_commission.py`, which was
never attempted and is not costed. Until that happens these JSON files are the
only surviving record of those measurements.

Seeds `11111`, `22222`, `33333` are the seed-repeat arms that established the
`pool1` deficit as 0.9737 +/- 0.0021 rather than seed noise.

## `*.log` — 28 files, render provenance for deleted TIFFs

One log per render from the band-count sweep and the base-band isolation arms.
Each carries the exact flag set, the resolved merge backend, the binary
version, and the per-level statistics printed at merge time. The TIFFs they
describe are gone; these logs are what makes the deletions honest, because
they record the command that produced each one.

**REGENERABLE**, unlike the JSON. The scripts are committed
(`bandsweep_render.ps1`, `baseband_render.ps1`) and their inputs are the
owner's read-only captures, so any of these renders can be reproduced. They
cost minutes each, not hours.

## What is NOT here, and cannot be

The six soft-gate reachability renders of `109MSDCF` were deleted. Their
numbers are recorded in full in Addendum L, and the exact six-arm recipe with
its pre-registered predictions is in `PREREG-SOFTGATE.md`, committed before
the arms ran. Rebuilding takes about three minutes. `vd_softgate_gate.py`
will fail loudly until they exist again — that is its commissioned behaviour
on a missing arm, not a regression.
