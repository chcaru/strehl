"""S3 -- the through-focus curve at every chosen ROI, from an INDEPENDENT decode.

Decodes all 299 frames with `rawpy`, extracts the four fixed 512x512 plane
windows, and scores each. `strehl`'s own focus measure is never consulted, so
"the sharpest frame that went in" is decided by an instrument that shares no
code with the thing under test.

Also caches the crop cube so the comparison and its controls can be re-run
without re-decoding.
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m95lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
CUBE = os.path.join(L.OUT, "m93_crops_v2.npy")
WIN = 512


def _one(job):
    path, wins = job
    rf = L.decode_raw(path)
    g = L.green_mean_plane(rf.cfa)
    return np.stack([g[y : y + WIN, x : x + WIN] for (x, y) in wins]).astype(np.float32)


def main() -> int:
    rois = json.load(open(os.path.join(OUTDIR, "s2b_rois.json"), encoding="utf-8"))
    names = list(rois["chosen"].keys())
    wins = [(rois["chosen"][n]["x"], rois["chosen"][n]["y"]) for n in names]
    paths = sorted(
        os.path.join(L.STACK, f) for f in os.listdir(L.STACK) if f.lower().endswith(".arw")
    )
    n = len(paths)
    print(f"decoding {n} frames into {len(names)} windows: {list(zip(names, wins))}")

    if os.path.exists(CUBE):
        cube = np.load(CUBE)
        print(f"cached cube    : {CUBE}  {cube.shape}")
    else:
        t0 = time.time()
        cube = np.zeros((n, len(names), WIN, WIN), dtype=np.float32)
        with ProcessPoolExecutor(max_workers=8) as ex:
            for i, arr in enumerate(ex.map(_one, [(p, wins) for p in paths], chunksize=4)):
                cube[i] = arr
                if (i + 1) % 50 == 0:
                    print(f"  {i+1:3d}/{n}  {time.time()-t0:6.1f}s", flush=True)
        np.save(CUBE, cube)
        print(f"wrote cube     : {CUBE}  {cube.shape}  {time.time()-t0:.1f}s")

    # Focus score per frame per window: high-pass energy, black-subtracted.
    scores = np.zeros((n, len(names)))
    for k in range(len(names)):
        for i in range(n):
            g = cube[i, k].astype(np.float64) - 512.0
            d = g - L.gaussian_blur(g, 2.0)
            scores[i, k] = float((d * d).mean())

    res = {}
    print()
    for k, nm in enumerate(names):
        s = scores[:, k]
        peak = int(np.argmax(s))
        top5 = np.argsort(s)[::-1][:5]
        # Half-width of the focus peak, in frames: where the curve falls to half
        # its peak height above its own floor.
        floor = float(np.percentile(s, 10))
        half = floor + 0.5 * (s[peak] - floor)
        above = np.where(s >= half)[0]
        width = int(above.max() - above.min() + 1) if above.size else 0
        res[nm] = dict(
            window=wins[k],
            peak_frame=peak,
            peak_score=float(s[peak]),
            floor_score=floor,
            contrast=float(s[peak] / max(floor, 1e-9)),
            top5=[int(v) for v in top5],
            fwhm_frames=width,
            scores=[float(v) for v in s],
        )
        print(
            f"{nm:<14} peak frame {peak:3d}  score {s[peak]:10.1f}  "
            f"floor {floor:9.1f}  contrast {s[peak]/max(floor,1e-9):7.2f}x  "
            f"FWHM {width:3d} frames  top5 {list(top5)}"
        )

    dst = os.path.join(OUTDIR, "s3_focus.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump({"names": names, "wins": wins, "res": res}, f, indent=2)
    print(f"\nwrote          : {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
