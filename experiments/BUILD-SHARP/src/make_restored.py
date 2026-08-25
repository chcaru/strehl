"""Write a restored copy of a rendered arm, so the ESF instrument can score it.

The restoration is measured the same way every other arm is: as a new arm under
`renders/<subject>/`, read by `esf.py` through `m88blib`, scored as a paired
10-90 ESF rise against the arm it was made from. It is NOT scored by any
high-pass energy statistic -- a linear boost of high frequencies raises
mean|grad| by construction, which is precisely the reading AGENTS rule 18 and
this project's own C3 control (M20 §6, an information-free filter moving a
gradient metric 8.25x) say is worthless as evidence.

The binned render is on the CFA quad plane -- the grid the gather actually ran
on -- so `grid_factor = 1.0` here and no factor-of-two argument is needed. That
is why the measurement is done on the binned arm and the demosaiced arm is only
ever LOOKED at.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import restore as R  # noqa: E402

RENDERS = Path(r"C:\dev\strehl-out\BUILD-SHARP\renders")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--out-arm", required=True)
    ap.add_argument("--grid-factor", type=float, default=1.0)
    ap.add_argument("--gain-cap", type=float, default=1.7)
    ap.add_argument("--kernel", default="catmull-rom")
    a = ap.parse_args()

    src = RENDERS / a.subject / a.arm / "linear.tif"
    arr = tifffile.imread(str(src))
    assert arr.dtype == np.uint16, f"{src} is {arr.dtype}, not uint16 (rule 7)"
    out = np.empty(arr.shape, dtype=np.float64)
    diag = {}
    for c in range(arr.shape[2]):
        out[:, :, c], diag = R.restore(arr[:, :, c].astype(np.float64),
                                       kernel=a.kernel,
                                       grid_factor=a.grid_factor,
                                       gain_cap=a.gain_cap)
    clipped = float(np.mean(out > 65535.0))
    out = np.clip(out, 0.0, 65535.0).astype(np.uint16)

    dst = RENDERS / a.subject / a.out_arm
    dst.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(str(dst / "linear.tif"), out)
    rec = dict(source=str(src), kernel=a.kernel, grid_factor=a.grid_factor,
               gain_cap=a.gain_cap, clipped_fraction=clipped, **diag)
    (dst / "cmd.txt").write_text(
        "restored arm, not a render\n"
        + "\n".join(f"{k:20}: {v}" for k, v in rec.items()) + "\n")
    print(json.dumps(rec, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
