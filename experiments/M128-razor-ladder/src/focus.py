"""M-PHASE0-EDGE / focus — sweep a bracket for the frame where the edge is sharpest.

A razor blade lying flat has its cutting edge at one depth but its bevel spans a
range of depths, so the bevel highlight and the silhouette edge come into focus
on different frames. Choosing a frame by eye, or by a whole-frame sharpness
metric, therefore need not choose the frame that focuses the edge.

This registers every column on its own 50%-crossing, averages the ESF, and
reports metrics that are local to the transition and so are not moved by the
bevel ridge further out:

  step_dn     ESF(-1 px) - ESF(+1 px), the contrast actually carried by the step
  maxgrad     peak |dESF/dx| in DN per green px
  w50         width in green px over which the ESF falls through the middle half
              of `step_dn`, centred on the crossing

Reported per frame so the plateau, not a single frame, decides best focus.
"""

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import geom  # noqa: E402


def metrics(path, mode, bright_first, x0, x1, band, half=8):
    g1, _g2, black = geom.read_greens(path)
    a = geom.orient(g1, mode)
    b0, b1 = band if band else geom.find_band(a)[:2]
    sl = np.ascontiguousarray(a[:, x0:x1])
    x, y, hi, lo = geom.crossings(sl, b0, b1, bright_first)
    if len(x) < 128:
        return dict(status=f"few columns ({len(x)})")
    p, xn, r3, keep = geom.fit_poly(x, y, geom.POLY_ORDER)
    e = geom.esf(sl, x, np.polyval(p, xn), keep, bright_first,
                 half=half, bin_w=0.0625)
    if not e:
        return dict(status="no esf")
    cc, ee, nl = e
    # local levels one px either side of the crossing
    def at(u):
        return float(np.interp(u, cc, ee))
    step = at(-1.0) - at(1.0)
    d = np.gradient(ee, cc)
    core = np.abs(cc) <= 3.0
    maxgrad = float(-np.min(d[core]))
    lvl_hi, lvl_lo = at(-1.0), at(1.0)
    t75 = lvl_lo + 0.75 * (lvl_hi - lvl_lo)
    t25 = lvl_lo + 0.25 * (lvl_hi - lvl_lo)

    def cross(t):
        for i in range(len(cc) - 1):
            if cc[i] > 3.0:
                break
            if cc[i] < -3.0:
                continue
            if ee[i] >= t > ee[i + 1]:
                u = (ee[i] - t) / max(ee[i] - ee[i + 1], 1e-9)
                return float(cc[i] + u * (cc[i + 1] - cc[i]))
        return None

    a75, a25 = cross(t75), cross(t25)
    w50 = (a25 - a75) if (a75 is not None and a25 is not None) else None
    return dict(step_dn=step, maxgrad=maxgrad, w50=w50, res3_px=r3,
                n_cols=int(keep.sum()), n_lines=nl,
                angle_deg=float(np.degrees(np.arctan(
                    np.polyfit(x[keep], y[keep], 1)[0]))),
                contrast_dn=float(np.median(hi) - np.median(lo)))


def _job(args):
    i, path, mode, bf, x0, x1, band, half = args
    try:
        m = metrics(path, mode, bf, x0, x1, band, half)
    except Exception as exc:                     # noqa: BLE001
        m = dict(status=f"error: {type(exc).__name__}: {exc}")
    m["index"] = i
    m["frame"] = Path(path).name
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stack")
    ap.add_argument("--orient", choices=["h", "v"], required=True)
    ap.add_argument("--bright-first", action="store_true")
    ap.add_argument("--x0", type=int, default=1400)
    ap.add_argument("--x1", type=int, default=2400)
    ap.add_argument("--band", nargs=2, type=int, default=None)
    ap.add_argument("--half", type=int, default=8)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    arws = sorted(Path(args.stack).glob("*.ARW"))
    picks = list(enumerate(arws))[::args.every]
    band = tuple(args.band) if args.band else None
    jobs = [(i, str(p), args.orient, args.bright_first, args.x0, args.x1,
             band, args.half) for i, p in picks]
    print(f"# {Path(args.stack).name}: {len(arws)} frames, sweeping {len(jobs)}, "
          f"cols {args.x0}..{args.x1}, half {args.half} px")
    print(f"{'idx':>4} {'frame':>13} {'step_dn':>8} {'maxgrad':>8} {'w50':>7} "
          f"{'ang':>8} {'res3':>6} {'ncol':>5}")
    out = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for m in ex.map(_job, jobs):
            out.append(m)
            if "status" in m:
                print(f"{m['index']:4d} {m['frame']:>13} {m['status']}")
            else:
                w = f"{m['w50']:.3f}" if m["w50"] is not None else "  -  "
                print(f"{m['index']:4d} {m['frame']:>13} {m['step_dn']:8.1f} "
                      f"{m['maxgrad']:8.1f} {w:>7} {m['angle_deg']:+8.4f} "
                      f"{m['res3_px']:6.3f} {m['n_cols']:5d}")
            sys.stdout.flush()
    ok = [m for m in out if "status" not in m]
    if ok:
        best = max(ok, key=lambda m: m["maxgrad"])
        print(f"\nsharpest by maxgrad: [{best['index']}] {best['frame']}  "
              f"maxgrad {best['maxgrad']:.1f}  step {best['step_dn']:.1f}  "
              f"w50 {best['w50']}")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, indent=1))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    main()
