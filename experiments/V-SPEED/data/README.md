# V-SPEED banked evidence

Every number in `docs/research/V-SPEED.md` and `docs/research/V-SPEED-HALO.md`
is re-derived from the files in this directory. Nothing in either report
depends on scratch that no longer exists.

    timing/   97 files  0.89 MB   read by verify.py     (end-to-end timing arms)
    halo/     59 files  0.16 MB   read by haloverify.py (halo instrument + audits)

Both verifiers resolve this directory first and fall back to the old scratch
paths only if it is missing, so a fresh clone can certify both reports with no
setup:

    python experiments\V-SPEED\verify.py                 # 6 certified + 3 uncertified = 9   GREEN
    python experiments\V-SPEED\verify.py --commission    # 5/5
    python experiments\V-SPEED\haloverify.py             # 35 certified + 0 reversed = 35    GREEN
    python experiments\V-SPEED\haloverify.py --commission # 5/5

This was verified by hiding both scratch directories and re-running all four
commands, rather than by assuming the path change took effect.

## Regenerating the heavy scratch that was deleted

10.18 GB of renders under `D:\strehl-out\V-SPEED-HALO\` were deleted after
every number they carried had been reduced into this directory. All of it
regenerates from committed scripts plus the owner's read-only originals under
`D:\personal\macro\` — the command is the artifact, not the pixels.

| Deleted | GB | Regenerate with |
|---|---:|---|
| `sweep\<subject>\{baseline,bands5,plainmean}.tiff` | 9.03 | `experiments\V-SPEED\sweep.ps1 -Subject <name>` |
| `hullcommission\` | 0.92 | `experiments\V-SPEED\hullcommission.ps1` |
| `cache\` (warp cache) | 0.22 | regenerated automatically on the next render |
| `inertness\` | ~0 | `experiments\V-SPEED\inertness.ps1` |

Scripts that consume the deleted renders — `noiseaudit.py`, `abscore.py`, and
`plantrim.py`'s default `--master` — therefore need a re-render before they can
run again. The verifiers do not: they read only this directory.

## What is NOT recoverable from here

`plantrim.py --specificity` builds its own synthetic images at run time and
needs no scratch, so the specificity result regenerates in full. But the
per-subject **pixels** are gone. If a future lane disputes a number in either
report, it must re-render via the table above rather than re-inspect. That is a
deliberate trade and it is the reason every figure was reduced to JSON here
first.
