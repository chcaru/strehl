"""Put all three statistics on one axis: equivalent Gaussian blur, in pixels.

The chain controls (build_controls.py, measured through measure.py) showed that
the three statistics have very different dynamic ranges. A plainly visible
0.8 px blur moves S1 by 3.07x but S2 by only 1.074x and S3 by 1.140x. So a
table of raw ratios makes S1 look like a huge effect and S2 like nothing, when
they may be reporting the same physical difference.

This converts each ratio into the ONE number a photographer can act on: how
many pixels of Gaussian blur separate the two arms.

  For each tile and each statistic, blur the MERGE tile through a ladder until
  its statistic falls to the ARGMAX tile's value. The sigma where they meet is
  the equivalent blur, positive meaning the merge is sharper by that much. If
  the argmax tile already scores lower than the merge tile cannot reach, the
  ladder is run on the ARGMAX tile instead and the sign flips.

  Every statistic is monotone in blur -- that is what commission.py verified
  and it is what makes the inversion well posed.

It reads the tile coordinates measure.py already chose. It does NOT re-choose
sites, so it cannot smuggle in a site preference; it re-uses the ones picked on
the mean of both arms.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from stats import STATS  # noqa: E402

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS")
RENDERS = OUT / "renders"
LADDER = np.concatenate([[0.0], np.arange(0.05, 2.51, 0.05)])


def green(p):
    img = tifffile.imread(str(p))
    assert img.dtype == np.uint16
    return img[:, :, 1].astype(np.float64)


def invert(t_from, target, fn):
    """Sigma at which blurring t_from drives fn down to `target`."""
    prev_s, prev_v = 0.0, fn(t_from)
    if target >= prev_v:
        return 0.0
    for s in LADDER[1:]:
        v = fn(gaussian_filter(t_from, s))
        if v <= target:
            w = 0.0 if prev_v == v else (prev_v - target) / (prev_v - v)
            return float(prev_s + w * (s - prev_s))
        prev_s, prev_v = s, v
    return float(LADDER[-1])


def main():
    src = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "measure-subjects.json"
    data = json.loads(src.read_text(encoding="utf8"))
    out = []
    for rec in data:
        subj = rec["subject"]
        d = RENDERS / subj
        gm, ga = green(d / "merge.tif"), green(d / "argmax.tif")
        Tm = rec["tiles"][0]["tile_px_merge"] if rec["tiles"] else 0
        rows = []
        for t in rec["tiles"]:
            x, y = t["merge_xy"]
            ax, ay = t["argmax_xy"]
            Ta = t["tile_px_argmax"]
            tm = gm[y:y + Tm, x:x + Tm]
            ta = ga[ay:ay + Ta, ax:ax + Ta]
            r = dict(tile=t["tile"], match=t["match"])
            for k, fn in STATS.items():
                vm, va = fn(tm), fn(ta)
                if va <= vm:
                    r[f"{k}_blur_px"] = invert(tm, va, fn)       # merge sharper
                else:
                    r[f"{k}_blur_px"] = -invert(ta, vm, fn)      # argmax sharper
            rows.append(r)
        rec_out = dict(subject=subj, tiles=rows)
        out.append(rec_out)
        print(f"\n=== {subj}")
        for k in STATS:
            v = [r[f"{k}_blur_px"] for r in rows]
            print(f"   {k:<10} equivalent blur  median {np.median(v):+6.3f} px   "
                  f"(per tile {' '.join(f'{x:+.2f}' for x in v)})")
    p = OUT / (src.stem.replace("measure", "blureq") + ".json")
    p.write_text(json.dumps(out, indent=1), encoding="utf8")
    print(f"\n+ = the shipped merge resolves finer; - = argmax-baseline does.")
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
