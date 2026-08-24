"""M97 bars E3/E3b: is the n_eff map CONNECTED to the estimator?

Cross-checks the mean of the exported TIFF against the `mean n_eff` scalar the
run prints from an INDEPENDENT computation in `report()`. A file that exists is
not an observation; a map that reproduces a separately-computed scalar is.

    python neffstat.py <map.tiff> <run.log>
"""

import re
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
tiff, log = sys.argv[1], sys.argv[2]

a = np.array(Image.open(tiff))
mean = float(a.mean())
print(f"file        : {tiff}")
print(f"shape/dtype : {a.shape} {a.dtype}")
print(f"range       : {a.min()}..{a.max()}  distinct {len(np.unique(a))}")
print(f"map mean    : {mean:.4f}")

# The gate table row: gate, tol, mean n_eff, n_eff=1 %, boundary %, sigma gain
text = open(log, encoding="utf-8", errors="replace").read()
rows = re.findall(
    r"^\s*(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)%", text, re.M
)
if not rows:
    raise SystemExit("PARSE FAILED: no gate-calibration row found in " + log)
if len(rows) != 1:
    raise SystemExit(f"AMBIGUOUS: {len(rows)} gate rows found; expected 1")

gate, _tol, printed, _one = rows[0]
printed = float(printed)
delta = abs(mean - printed)
print(f"printed mean: {printed:.4f}  (gate {gate}, independent computation)")
print(f"delta       : {delta:.5f}")
print(f"distinct>1  : {len(np.unique(a)) > 1}")
print("E3: " + ("PASS" if delta < 0.01 and len(np.unique(a)) > 1 else "FAIL"))
