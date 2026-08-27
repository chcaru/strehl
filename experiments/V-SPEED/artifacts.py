"""Confirm each arm's end artifact is a real merged image.

Speed is what V-SPEED measures; quality belongs to other lanes. This checks
only that the file on disk is a plausible merge -- right rank, non-degenerate
dimensions, not blank, not a single flat value -- so that no arm is credited
with a fast run that produced nothing. One line per file.
"""

import glob
import os
import sys

import numpy as np
import tifffile


def describe(path):
    a = tifffile.imread(path)
    a = np.asarray(a)
    if a.ndim == 2:
        a = a[:, :, None]
    h, w, c = a.shape
    flat = a.reshape(-1, c)
    # subsample for speed; a blank frame is blank everywhere
    s = flat[:: max(1, flat.shape[0] // 400000)]
    return {
        "file": os.path.basename(path),
        "bytes": os.path.getsize(path),
        "shape": (h, w, c),
        "dtype": str(a.dtype),
        "min": int(s.min()),
        "max": int(s.max()),
        "mean": float(s.mean()),
        "std": float(s.std()),
        "unique_sample": int(np.unique(s[:, 0]).size),
    }


def main():
    paths = []
    for pat in sys.argv[1:]:
        paths.extend(sorted(glob.glob(pat)))
    for p in paths:
        d = describe(p)
        verdict = "REAL" if d["std"] > 1.0 and d["unique_sample"] > 100 else "SUSPECT"
        print(
            f"{d['file']:<22} {d['shape'][1]}x{d['shape'][0]}x{d['shape'][2]} {d['dtype']:<7} "
            f"min={d['min']:<6} max={d['max']:<6} mean={d['mean']:>10.1f} sd={d['std']:>9.1f} "
            f"uniq={d['unique_sample']:<6} {d['bytes']:>12,} B  {verdict}"
        )


if __name__ == "__main__":
    main()
