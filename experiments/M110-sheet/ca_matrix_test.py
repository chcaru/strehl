"""Is the section 14 green/blue coupling just the sRGB colour matrix?

Section 14 measured, on --srgb renders: CA changes green on 94.4% of pixels
and blue on 67.7%, with |dG|/|dR| CONSTANT at 0.087..0.110 across radius, and
recorded the mechanism as UNIDENTIFIED (candidates: election response,
demosaic coupling, and later an extra resampling pass).

ORCH/M113 propose a fourth: camera_to_srgb is non-diagonal, so output green
carries camera red by construction. merge_cmd.rs:77 confirms --srgb applies
"the sRGB transfer curve AND the camera's colour matrix. For looking at, NOT
for measuring." A constant ratio across radius is exactly a fixed linear
coupling's signature.

Bars are registered in ca_matrix_prereg.py, run before these renders were
measured. P2: linear ratio COLLAPSES (< 0.02) => matrix explains it.
P3: linear ratio SURVIVES (>= 0.05) => a real mechanism remains.

The sharp test is the SIGNED ratio, not the magnitude. The matrix predicts
dG_out = M[1][0]/M[0][0] * dR_out = -0.0704 * dR_out -- a specific NEGATIVE
constant. Election or demosaic coupling has no reason to hold a fixed sign.
Magnitude alone cannot tell those apart; this is the same lesson as scoring
the overshoot conjunction rather than the sign flip alone (section 16.2).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import tifffile

PRED_G = -0.1152 / 1.6361   # -0.0704, from ca_matrix_prereg.py
PRED_B = -0.0047 / 1.6361   # -0.0029


def load(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    if a.ndim != 3 or a.shape[2] < 3:
        raise SystemExit(f"{p}: expected HxWx3, got {a.shape}")
    return a[:, :, :3].astype(np.float64)


def radial(shape) -> np.ndarray:
    h, w = shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    half_diag = np.hypot(cx, cy)
    return np.hypot(xx - cx, yy - cy) / half_diag


def analyse(off: Path, on: Path, label: str, thresh_frac: float) -> dict:
    a, b = load(off), load(on)
    if a.shape != b.shape:
        raise SystemExit(f"{label}: shape mismatch {a.shape} vs {b.shape}")

    d = b - a
    dR, dG, dB = d[:, :, 0], d[:, :, 1], d[:, :, 2]

    # Threshold on |dR| so the ratio is not dominated by divide-by-noise.
    # Fraction of the render's own full scale, so it transfers between the
    # linear and sRGB pairs without assuming a common absolute level.
    scale = float(np.percentile(np.abs(dR), 99.9))
    thresh = thresh_frac * scale
    m = np.abs(dR) > thresh
    n = int(m.sum())
    if n < 1000:
        raise SystemExit(f"{label}: only {n} pixels above threshold")

    rG = dG[m] / dR[m]
    rB = dB[m] / dR[m]
    r = radial(a.shape)[m]

    print("=" * 72)
    print(f"{label}")
    print(f"  shape {a.shape}  |dR| p99.9 = {scale:.1f}  thresh = {thresh:.1f}"
          f"  n = {n:,} ({100.0*n/dR.size:.2f}% of pixels)")
    print(f"  pixels changed: R {100.0*np.mean(dR!=0):.1f}%  "
          f"G {100.0*np.mean(dG!=0):.1f}%  B {100.0*np.mean(dB!=0):.1f}%")
    print()
    print(f"  SIGNED  median dG/dR = {np.median(rG):+.4f}   "
          f"(matrix predicts {PRED_G:+.4f})")
    print(f"  SIGNED  median dB/dR = {np.median(rB):+.4f}   "
          f"(matrix predicts {PRED_B:+.4f})")
    print(f"  |dG|/|dR| median     = {np.median(np.abs(rG)):.4f}")
    print(f"  |dB|/|dR| median     = {np.median(np.abs(rB)):.4f}")
    print(f"  frac(dG/dR < 0)      = {100.0*np.mean(rG < 0):.1f}%  "
          f"(matrix predicts ~100%, a fixed negative coupling)")
    print()
    print("  signed median dG/dR by radius (constancy is the matrix signature):")
    for lo in np.arange(0.0, 1.0, 0.1):
        sel = (r >= lo) & (r < lo + 0.1)
        if sel.sum() > 200:
            print(f"    r {lo:.1f}-{lo+0.1:.1f}  {np.median(rG[sel]):+.4f}"
                  f"   n={int(sel.sum()):>9,}")
    return {"med_signed_g": float(np.median(rG)),
            "med_abs_g": float(np.median(np.abs(rG))),
            "med_signed_b": float(np.median(rB))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=r"C:\dev\strehl-out\M110-sheet\bee-3-cpl")
    ap.add_argument("--thresh-frac", type=float, default=0.05)
    args = ap.parse_args()
    d = Path(args.dir)

    print(__doc__)
    print("--srgb turns --demosaic ON BY DEFAULT (stack --help), so the naive")
    print("sRGB-vs-linear comparison changes TWO things at once and a collapse")
    print("could be the demosaic -- itself a section 14 candidate -- rather than")
    print("the matrix. Three cells decompose it, one factor at a time.")
    print()
    a = analyse(d / "default.tif", d / "ca.tif",
                "A: sRGB + demosaic   -- what section 14 measured",
                args.thresh_frac)
    b = analyse(d / "lind-default.tif", d / "lind-ca.tif",
                "B: LINEAR + demosaic -- matrix removed, demosaic HELD",
                args.thresh_frac)
    c = analyse(d / "lin-default.tif", d / "lin-ca.tif",
                "C: LINEAR + binned   -- matrix removed, demosaic removed",
                args.thresh_frac)

    print("=" * 72)
    print("TWO-FACTOR DECOMPOSITION of |dG|/|dR|")
    ga, gb, gc = a["med_abs_g"], b["med_abs_g"], c["med_abs_g"]
    print(f"  A sRGB+demosaic   {ga:.4f}")
    print(f"  B linear+demosaic {gb:.4f}   <- A to B isolates MATRIX + TRANSFER")
    print(f"  C linear+binned   {gc:.4f}   <- B to C isolates DEMOSAIC")
    print()
    print(f"  matrix effect   A -> B : {ga:.4f} -> {gb:.4f}  ({ga/max(gb,1e-9):.1f}x)")
    print(f"  demosaic effect B -> C : {gb:.4f} -> {gc:.4f}  ({gb/max(gc,1e-9):.1f}x)")
    print()
    print(f"  signed dG/dR      A {a['med_signed_g']:+.4f}   "
          f"B {b['med_signed_g']:+.4f}   C {c['med_signed_g']:+.4f}")
    print(f"  matrix predicts for A: {PRED_G:+.4f}")
    print()
    print("VERDICT (bars registered in ca_matrix_prereg.py)")
    if gb < 0.02:
        print("  P2 PASS -- removing the MATRIX ALONE collapses the ratio.")
        print("     The colour matrix explains the section 14 coupling.")
    elif gb >= 0.05:
        print("  P3 -- ratio SURVIVES with the matrix removed and demosaic held.")
        print("     The matrix is NOT the whole story; a real mechanism remains.")
    else:
        print("  INDETERMINATE -- between the registered bars (0.02..0.05).")
        print("     Report as such; do not round toward either conclusion.")


if __name__ == "__main__":
    main()
