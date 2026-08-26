"""Run ORCH's flatnoise.py VERBATIM on BUILD-BLEND's own paired renders.

The only thing changed is the input directory. ORCH's measurement logic --
the high-pass, the arm-average tile selection, the MAD sigma, the sigma/mean
normalisation -- is imported and executed unmodified, so a disagreement
between this run and ORCH's cannot be an instrument difference.

Purpose: ORCH reported +32.1% added flat-region noise on couch-fibers-cpl
using two pinned binaries. BUILD-BLEND's own report reads 1.0015 on the same
subject. ORCH listed three candidate causes -- different tiles, different
high-pass radius, different renders -- and did not reconcile them.

Running ORCH's instrument on BUILD-BLEND's renders separates them:
  * result near +32%  -> the renders agree; the earlier 1.0015 was BUILD-BLEND's
                         own instrument and ORCH's number stands.
  * result near   0%  -> the instruments agree; the gap is in the RENDERS, i.e.
                         the two pinned binaries are not the two arms compared
                         here.
"""
import importlib.util
import sys
from pathlib import Path

ORCH = Path(r"C:\dev\strehl-out\ORCH-100\flatnoise.py")
FLIP = Path(r"C:\dev\strehl-out\BUILD-BLEND\flip")
STAGE = Path(r"C:\dev\strehl-out\BUILD-BLEND\flatnoise-mine")

# 'before' is the shipped-before merge (estimator), 'after' is this arm
# (pyramid) -- the same polarity ORCH's -before/-after naming carries.
PAIRS = [p.name[: -len("--estimator.tiff")]
         for p in sorted(FLIP.glob("*--estimator.tiff"))]

STAGE.mkdir(parents=True, exist_ok=True)
staged = 0
for subj in PAIRS:
    for arm, suffix in (("estimator", "before"), ("pyramid", "after")):
        src = FLIP / f"{subj}--{arm}.tiff"
        dst = STAGE / f"{subj}-{suffix}.tiff"
        if not src.exists():
            print(f"  skip {subj}: no {src.name}")
            break
        if not dst.exists():
            # Hard link: same volume, no 188 MB copy, identical bytes.
            dst.hardlink_to(src)
    else:
        staged += 1

print(f"staged {staged} subject pair(s) into {STAGE}")
if staged == 0:
    sys.exit("nothing staged -- refusing to report a result on no input")

spec = importlib.util.spec_from_file_location("orch_flatnoise", ORCH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# The ONLY modification: where the inputs come from.
mod.TIFF_DIR = STAGE
print(f"ORCH's constants, unmodified: HP_RADIUS={mod.HP_RADIUS} "
      f"TILE={mod.TILE} N_TILES={mod.N_TILES}\n")
sys.exit(mod.main())
