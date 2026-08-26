"""Test every merge arm against the cached warped-frame hull, and print a
partition of ARMS that sums, so a skipped arm cannot be read as a passing one.

Requirements this satisfies, from ORCH:
  2. violating fraction per band and per channel, whole-frame (internal
     control) and restricted to the bbox
  3. excursion in units of hull span
  5. a partition that sums -- requested / scored / missing
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from bhull2 import BBOX, BBOX_FULL, CHANNELS, HDR, bands_of, load16, row, score

ARMS = [
    ("W-pyramid", "SHIPPED: exponent 2, sharpen 1.4, 7 bands"),
    ("W-uniform", "NULL C1: exponent ~0, sharpen 1.0 -> weights shared+uniform"),
    ("W-e1s1", "exponent 1, sharpen 1.0 -> flat ramp, mild selection"),
    ("W-bands1", "1 Laplacian level: least room for per-band disagreement"),
    ("W-estimator", "the other backend entirely (elect-then-average)"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--levels", type=int, default=7)
    ap.add_argument("--guard", type=float, default=1.0)
    ap.add_argument("--bands", action="store_true")
    ap.add_argument("--plant", type=float, default=0.0)
    ap.add_argument("--plant-arm", default="W-uniform")
    ap.add_argument("--plant-box", default="1000,1200,1000,1200")
    a = ap.parse_args()

    cache, mdir = Path(a.cache), Path(a.dir)
    lo = np.load(cache / "lo.npy").astype(np.float32)
    hi = np.load(cache / "hi.npy").astype(np.float32)
    span = hi - lo
    y0, y1, x0, x1 = BBOX

    print("=== BUILD-HULL :: arms vs the warped-frame hull ===")
    print(f"  hull cache   : {cache}")
    print(f"  guard        : +/- {a.guard:g} DN")
    print(f"  bbox full-res: y{BBOX_FULL[0]}..{BBOX_FULL[1]} x{BBOX_FULL[2]}..{BBOX_FULL[3]}")
    print(f"  bbox here    : y{y0}..{y1} x{x0}..{x1}  (renders are half-res)")
    print(f"  arms REQUESTED: {len(ARMS)}")

    scored, missing = [], []
    for tag, _ in ARMS:
        (scored if (mdir / f"merge-{tag}.tiff").exists() else missing).append(tag)
    print(f"  arms SCORED   : {len(scored)}  {scored}")
    print(f"  arms MISSING  : {len(missing)}  {missing}")
    assert len(scored) + len(missing) == len(ARMS), "arm partition does not sum"

    regions = {"whole (control)": (slice(None), slice(None)),
               "bbox": (slice(y0, y1 + 1), slice(x0, x1 + 1))}

    print("\n--- WHOLE IMAGE ---")
    print(HDR)
    summary = {}
    for tag, note in ARMS:
        p = mdir / f"merge-{tag}.tiff"
        if not p.exists():
            print(f"  {tag:<26} {'--':<4} MISSING -- not scored ({note})")
            continue
        m = load16(p).astype(np.float32)
        if a.plant and tag == a.plant_arm:
            py0, py1, px0, px1 = (int(t) for t in a.plant_box.split(","))
            m[py0:py1, px0:px1, :] += a.plant
            print(f"  >>> PLANT {a.plant:+.0f} DN into {tag} y{py0}:{py1} x{px0}:{px1} "
                  f"= {(py1 - py0) * (px1 - px0) * 3} samples")
        v = np.where(m < lo, m - lo, np.where(m > hi, m - hi, 0.0))
        for rname, (ys, xs) in regions.items():
            for ci, cn in enumerate(CHANNELS + ("all",)):
                if cn == "all":
                    vv, ss = v[ys, xs, :], span[ys, xs, :]
                else:
                    vv, ss = v[ys, xs, ci], span[ys, xs, ci]
                r = score(vv, ss, a.guard)
                print(row(f"{tag} {rname}", cn, r))
                if cn == "all":
                    summary[(tag, rname)] = r
        print()

    if a.bands:
        print("--- PER BAND (my own linear Laplacian; see bhull2 docstring) ---")
        print(HDR)
        for tag, _ in ARMS:
            p = mdir / f"merge-{tag}.tiff"
            if not p.exists():
                print(f"  {tag:<26} MISSING -- not scored")
                continue
            mb = bands_of(load16(p), a.levels)
            for b in range(a.levels + 1):
                blo = np.load(cache / f"blo{b}.npy")
                bhi = np.load(cache / f"bhi{b}.npy")
                sp = bhi - blo
                vv = np.where(mb[b] < blo, mb[b] - blo,
                              np.where(mb[b] > bhi, mb[b] - bhi, 0.0))
                nm = "base" if b == a.levels else f"d{b}" + ("(fine)" if b == 0 else "")
                for rname, (ys, xs) in regions.items():
                    for ci, cn in enumerate(CHANNELS):
                        print(row(f"{tag} {nm} {rname}", cn,
                                  score(vv[ys, xs, ci], sp[ys, xs, ci], a.guard)))
            print()

    print("=== HEADLINE (all channels, whole frame vs bbox) ===")
    print(f"  {'arm':<14} {'region':<16} {'rate':>9} {'below':>10} {'above':>10} "
          f"{'worst/span':>11} {'mean DN':>9}")
    for (tag, rname), r in summary.items():
        print(f"  {tag:<14} {rname:<16} {r['rate']:>8.4f}% {r['below']:>10} "
              f"{r['above']:>10} {r['worst_span']:>11.3f} {r['mean_dn']:>9.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
