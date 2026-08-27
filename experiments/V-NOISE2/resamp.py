"""resamp.py -- how much of a comparator's apparent quietness is resampling?

THE PROBLEM, and it is specific to `bee-1-cpl`.  geomcrop.py MEASURED that
align_image_stack -m did not crop bee's aligned set, it RESAMPLED it: the
output is 6200x4120 against strehl's 7032x4688, the two raster ratios agree to
0.32%, and both comparators fit a scale of 1.124-1.125 with a unimodal
interior maximum.  On `113MSDCF` and `119MSDCF` no such thing happened -- the
comparator raster is identical to strehl's and the fitted scale is 1.004-1.005.

So on bee, and on bee alone, the comparator arms have been through resampling
that strehl has not:

  1. Hugin DOWNSCALED every aligned frame by ~0.888 BEFORE enfuse and
     focus-stack fused them.  Downscaling averages neighbouring pixels, so
     this is a genuine reduction of the comparator's noise.
  2. hd2.py must UPSCALE the comparator by ~1.125 to put it on strehl's grid
     before differencing.  Interpolation correlates neighbours, so this
     further reduces its MEASURED high-frequency noise.

Both steps make the comparator look cleaner, so both run AGAINST strehl: any
strehl advantage measured on bee is a LOWER BOUND.  That is the safe
direction, which is exactly why it must be quantified rather than waved at --
"the error is in the conservative direction" is an argument, and a number is
a measurement.

WHAT THIS MEASURES.  strehl's own A/B pair is put through the same round trip
the comparator underwent -- downscale by 1/s, upscale by s, with the same
spline order hd2.py uses -- and its noise is measured before and after with
the LANE'S OWN statistic, imported from halfdiff.half_sigma, on the SAME
census FLAT tiles.  The drop is the size of the effect, measured on this
subject's own pixels.

    reported ratio = sigma(round-tripped) / sigma(original)

A ratio of 1.0 means resampling costs nothing and bee's numbers need no
discount.  A ratio of 0.8 means a comparator gets a free 1.25x noise
advantage from the pipeline before any merging happens, and bee's measured
advantage must be read against that.

CONTROL.  The identity arm resamples by 1.0 and must return 1.000 to within
the estimator's own floor.  Without it a ratio below 1 could be the round
trip, or could be any incidental cost of passing through zoom() twice.

Usage:  python resamp.py <key> [scale]
"""
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE"))
from noisefree import T, EDGE                                     # noqa: E402
from halfdiff import half_sigma                                   # noqa: E402

ROOT = r"C:\dev\strehl-out\V-NOISE2"
CHAN = ["luma  Y", "chroma R-Y", "chroma B-Y"]


def load(p):
    a = tifffile.imread(p)
    if a.ndim == 3 and a.shape[2] == 4:
        a = a[:, :, :3]
    return a.astype(np.float32)


def roundtrip(a, s, force=False):
    """Down by 1/s then up by s, per channel, order 3 -- hd2.py's resampler.

    `force` runs the zoom path even at s == 1.0.  Without it the identity
    control is a NO-OP BY CONSTRUCTION -- it returns `a.copy()` and the ratio
    is exactly 1.0000 on every channel no matter how badly the real arm is
    broken.  An arm whose answer is fixed in advance returning exactly that
    answer is not evidence, and M127 recorded this same defect under QUANT8:
    an exactly-1.000 reading from a fixed-by-construction arm is the cheapest
    defect detector there is, and it fires here.  With `force` the control
    passes through zoom() twice at unit scale, so it isolates the cost of the
    SCALE CHANGE from the cost of merely being resampled at all.
    """
    if abs(s - 1.0) < 1e-9 and not force:
        return a.copy()
    out = np.empty_like(a)
    for c in range(a.shape[2]):
        d = ndimage.zoom(a[:, :, c], 1.0 / s, order=3)
        u = ndimage.zoom(d, s, order=3)
        h = min(u.shape[0], a.shape[0])
        w = min(u.shape[1], a.shape[1])
        out[:, :, c] = 0.0
        out[:h, :w, c] = u[:h, :w]
    return out


def measure(A, B, cells):
    rows = []
    for (y, x) in cells:
        ta = A[y:y + T, x:x + T]
        tb = B[y:y + T, x:x + T]
        if ta.shape[0] != T or ta.shape[1] != T:
            continue
        if ta.mean() <= 1e-6 or tb.mean() <= 1e-6:
            continue
        r = half_sigma(ta, tb)
        if r is not None and np.all(np.isfinite(r)):
            rows.append(r)
    return np.array(rows)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    key = sys.argv[1]
    if len(sys.argv) > 2:
        scale = float(sys.argv[2])
    else:
        with open(os.path.join(ROOT, key, "geom.json"), encoding="utf-8") as fh:
            g = json.load(fh)
        ss = [v["scale"] for v in g.values() if v.get("ok")]
        if not ss:
            raise SystemExit(f"{key}: no successful geometry fit to take a scale from")
        scale = float(np.mean(ss))

    z = np.load(os.path.join(ROOT, key, "census.npz"))
    cells = [tuple(c) for c in z["cells"][z["flat"]]]
    A = load(os.path.join(ROOT, key, "arms", "strehl-A.tiff"))
    B = load(os.path.join(ROOT, key, "arms", "strehl-B.tiff"))

    print("=" * 92)
    print(f"resamp -- cost of the comparator's resampling, on {key}'s own strehl pixels")
    print("=" * 92)
    print(f"  scale from geom.json: {scale:.4f}   FLAT tiles: {len(cells)}   "
          f"tile {T} edge {EDGE}")

    base = measure(A, B, cells)
    print(f"\n  {'arm':28s} {'tiles':>6s} " + " ".join(f"{c:>13s}" for c in CHAN))
    print(f"  {'ORIGINAL':28s} {len(base):6d} " +
          " ".join(f"{v:13.6f}" for v in np.median(base, axis=0)))

    out = {"key": key, "scale": scale, "n_tiles": int(len(base))}
    for lab, s, force in (("COPY (inert, must be 1.000)", 1.0, False),
                          ("IDENTITY (zoom at s=1)", 1.0, True),
                          (f"ROUND TRIP (s={scale:.4f})", scale, False)):
        Ar = roundtrip(A, s, force)
        Br = roundtrip(B, s, force)
        m = measure(Ar, Br, cells)
        n = min(len(m), len(base))
        rat = np.median(m[:n] / base[:n], axis=0)
        print(f"  {lab:28s} {len(m):6d} " +
              " ".join(f"{v:13.6f}" for v in np.median(m, axis=0)))
        print(f"  {'  -> ratio vs ORIGINAL':28s} {'':6s} " +
              " ".join(f"{v:13.4f}" for v in rat))
        k = "copy" if (s == 1.0 and not force) else ("identity" if s == 1.0 else "roundtrip")
        out[k] = [float(v) for v in rat]

    cp = np.array(out["copy"])
    ctl = np.array(out["identity"])
    rt = np.array(out["roundtrip"])
    inert_ok = np.all(cp == 1.0)
    print(f"\n  COPY arm exactly 1.000 on all channels -> "
          f"{'as required (it is a no-op)' if inert_ok else 'FAIL -- the loader is not deterministic'}")
    print(f"  IDENTITY arm (real zoom, unit scale) moves the statistic by "
          f"{', '.join(f'{(v - 1) * 100:+.2f}%' for v in ctl)}")
    print(f"  -- that is the cost of BEING RESAMPLED, with no scale change, "
          f"and it is the floor the\n     round trip must be read against.")
    net = rt / ctl
    print(f"\n  NET effect of the {scale:.4f} scale change, above the "
          f"resampling floor: "
          f"{', '.join(f'{(v - 1) * 100:+.2f}%' for v in net)}")
    print(f"\n  READING.  The comparator's free noise reduction is "
          f"{', '.join(f'{1 / v:.3f}x' for v in rt)}")
    print(f"  ({', '.join(CHAN)}) from resampling alone, before any merging.")
    print(f"  A strehl advantage measured on {key} is therefore a LOWER BOUND, "
          f"and dividing it by these\n  factors gives the resampling-corrected "
          f"advantage:  corrected = measured * ratio.")
    out["net"] = [float(v) for v in net]
    p = os.path.join(ROOT, key, "resamp.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n  written {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
