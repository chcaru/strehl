"""Reconcile the per-octave view with the whole-image view by FOOTPRINT.

The raw per-octave DN shares are misleading and must not be reported alone.
detail0 has 8,250,880 samples per channel; the base octave has 532. So detail0
dominates any unweighted sum of |violation| simply by existing, even when its
per-sample excursion is small.

What actually reaches the viewer is the RECONSTRUCTION: a base coefficient is
upsampled through seven levels and lands on ~128x128 output pixels. So this
takes each octave's violation field, upsamples it back to full resolution the
same way the pyramid reconstructs, and reports how much output darkening each
octave is responsible for.

It also subtracts the NULL arm octave by octave. The finest octave violates in
every arm including the near-uniform-mean null, which makes it common-mode --
demosaic and CFA interpolation, not per-band selection. Reporting the shipped
arm's detail0 without that subtraction would credit the pyramid for a defect it
does not cause. The brief warned about exactly this trap for demosaic.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from bhull2 import load16
from octave import GUARD, pyr, up

LEVELS = 7


def viol_field(mb, los, his, b):
    return np.where(mb[b] < los[b], mb[b] - los[b],
                    np.where(mb[b] > his[b], mb[b] - his[b], 0.0))


def to_full(v, b, shapes):
    """Upsample band `b` back to full resolution the way the pyramid
    reconstructs, so its output footprint is represented honestly. Band b lives
    at pyramid level b, so it takes exactly b upsampling steps to reach level 0."""
    cur = v
    for lv in range(b, 0, -1):
        cur = up(cur, shapes[lv - 1])
    assert cur.shape[:2] == shapes[0][:2], f"band {b} did not reach full res"
    return cur


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="warp")
    ap.add_argument("--cache", default="warp/oct")
    ap.add_argument("--arm", default="W-pyramid")
    ap.add_argument("--null", default="W-uniform")
    a = ap.parse_args()
    mdir, cache = Path(a.dir), Path(a.cache)

    los = [np.load(cache / f"olo{b}.npy") for b in range(LEVELS + 1)]
    his = [np.load(cache / f"ohi{b}.npy") for b in range(LEVELS + 1)]
    shapes = [l.shape for l in los]

    out = {}
    for tag in (a.arm, a.null):
        mb = pyr(load16(mdir / f"merge-{tag}.tiff"), LEVELS)
        rows = []
        for b in range(LEVELS + 1):
            v = viol_field(mb, los, his, b)
            v = np.where(np.abs(v) > GUARD, v, 0.0)
            f = to_full(v, b, shapes)
            rows.append((float(np.abs(f).sum()), float(f.sum()),
                         int(np.count_nonzero(np.abs(v) > GUARD)), v.size))
        out[tag] = rows

    print(f"=== footprint-weighted octave attribution: {a.arm} vs null {a.null} ===")
    print("  Each octave's violation field upsampled to full resolution, so the")
    print("  numbers are output darkening, not coefficient counts.\n")
    print(f"  {'octave':<9} {'grid':>12} {'viol px':>10} {'rate':>8} "
          f"{'net DN (full-res)':>20} {'null net':>16} {'EXCESS over null':>18} {'share':>8}")

    sh, nl = out[a.arm], out[a.null]
    excess = [abs(sh[b][1] - nl[b][1]) for b in range(LEVELS + 1)]
    tot_ex = sum(excess)
    for b in range(LEVELS + 1):
        nm = "base" if b == LEVELS else f"detail{b}"
        g = f"{shapes[b][1]}x{shapes[b][0]}"
        s_abs, s_net, s_n, s_sz = sh[b]
        n_abs, n_net, n_n, n_sz = nl[b]
        print(f"  {nm:<9} {g:>12} {s_n:>10,} {100.0 * s_n / s_sz:>7.3f}% "
              f"{s_net:>20,.0f} {n_net:>16,.0f} {sh[b][1] - nl[b][1]:>18,.0f} "
              f"{100.0 * excess[b] / max(tot_ex, 1e-9):>7.3f}%")

    print(f"\n  total |excess over null|, full-res weighted : {tot_ex:,.0f} DN")
    coarse = sum(excess[1:])
    print(f"  detail0 (finest, COMMON-MODE with the null) : "
          f"{100.0 * excess[0] / max(tot_ex, 1e-9):.3f}%")
    print(f"  detail1..base (coarser octaves)             : "
          f"{100.0 * coarse / max(tot_ex, 1e-9):.3f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
