"""Where does the red residual live, relative to the fit's declared support?

The red lateral-CA coefficient in `A7C2_FE100GM_2XTC_X4CPL` declares
`support_r_max = 0.788`: the 20 ROIs it was fitted on span r = 0.208..0.788 of
the normalised radius, the outer two annuli are empty, and the corner is a
1.27x LINEAR EXTRAPOLATION -- "declared, not enforced". If that extrapolation is
what over-corrects red, the signature is specific and falsifiable:

    the residual R displacement must be near zero INSIDE  r < 0.788
    and must grow with radius OUTSIDE r > 0.788

If instead the residual is a constant fraction of radius everywhere, the
coefficient is simply the wrong size and the extrapolation is innocent. Those
two predictions differ in shape, not just magnitude, so the binning decides
between them rather than merely quantifying one.

Radius is normalised so that 1.0 is the CORNER, matching `support_r_max`, which
is the convention the profile record uses.

Usage:
    python radialprofile.py <image.tiff> [--tile 384]
"""

import argparse
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from chromashift import field  # noqa: E402

SUPPORT_R_MAX = 0.788


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--tile", type=int, default=384)
    args = ap.parse_args()

    img = np.asarray(tifffile.imread(args.image)).astype(np.float64)
    if img.ndim == 2:
        img = np.dstack([img] * 3)
    recs = field(img[:, :, :3], args.tile, 97.0)
    if not recs:
        print("no usable tiles")
        return 1
    r = np.array([q["r"] for q in recs])
    rn = r / r.max()
    print(f"image : {args.image}  tiles={len(recs)}  support_r_max={SUPPORT_R_MAX}")
    print(f"{'r bin':>12} {'n':>4} {'R radial px':>12} {'B radial px':>12}  region")
    edges = [0.0, 0.2, 0.35, 0.5, 0.65, 0.788, 0.9, 1.001]
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        m = (rn >= lo) & (rn < hi)
        if m.sum() == 0:
            continue
        rr = np.array([q["Rrad"] for q in recs])[m]
        bb = np.array([q["Brad"] for q in recs])[m]
        region = "INSIDE support" if hi <= SUPPORT_R_MAX + 1e-9 else "EXTRAPOLATED"
        print(f"  {lo:.3f}-{hi:.3f} {int(m.sum()):>4} {rr.mean():+12.4f} "
              f"{bb.mean():+12.4f}  {region}")

    ins = rn < SUPPORT_R_MAX
    out = ~ins
    rr = np.array([q["Rrad"] for q in recs])
    bb = np.array([q["Brad"] for q in recs])
    print(f"\n  INSIDE  r<{SUPPORT_R_MAX}: n={int(ins.sum()):d} "
          f"R={rr[ins].mean():+.4f} px  B={bb[ins].mean():+.4f} px")
    print(f"  OUTSIDE r>{SUPPORT_R_MAX}: n={int(out.sum()):d} "
          f"R={rr[out].mean():+.4f} px  B={bb[out].mean():+.4f} px")
    if ins.sum() and out.sum():
        print(f"  ratio OUTSIDE/INSIDE for R = "
              f"{rr[out].mean() / rr[ins].mean() if rr[ins].mean() != 0 else float('nan'):.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
