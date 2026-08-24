"""M87 s31f -- the veil's amplitude, against a LOCAL background model.

WHY THIS EXISTS.  86 measured the veil as "median DN at distance d from the
silhouette, minus a global quadratic fit".  Two things are wrong with that.

  - Distance from the subject is not independent of position in the frame.
    The subject fills the upper left, so every large-d pixel is lower right.
    The scene's own background gradient is aliased straight into the falloff
    curve.
  - The global quadratic could not hold the gradient anyway: its residual sd
    on the far field was 1736 DN, comparable to the 2951 DN it was being used
    to measure.  A model whose error is 59% of the signal is not a reference.

REPAIR.  Build the background reference LOCALLY: at every pixel, the mean of
far-field pixels within a large window.  A local reference follows whatever
gradient the scene has, of any order, and cancels it.  Pixels with too few
far-field neighbours are dropped rather than extrapolated into.

  BAR B11, three branches, on the peak of the local-residual falloff:
     >= 10 * one output code of ORCH's cast (1157 DN)
            -> the veil is a LARGE feature, "a few DN" is wrong
     <= 3 DN -> "a few DN" is right and my reading is wrong
     otherwise -> INTERMEDIATE, report the number

  CONTROL C-FAR.  The same pipeline run on distances measured from a mask of
  the same shape placed where there is no subject cannot show a hump.  Built
  by rotating the subject mask 180 degrees, which preserves its area, its
  perimeter and its shape statistics while destroying its registration to the
  image.  A hump under C-FAR would mean the estimator manufactures one.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy import ndimage
from PIL import Image

SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
X0, Y0, W, H = 700, 3150, 1100, 900
FARFIELD_D = 70          # px: beyond this a pixel defines background
WIN = 251                # px: local reference window
MIN_FAR = 0.06           # min fraction of the window that must be far field
B11_LARGE_CODES = 10.0
B11_FEW_DN = 3.0


def local_reference(g, far, win, min_far):
    m = far.astype(np.float32)
    num = ndimage.uniform_filter(g * m, win)
    den = ndimage.uniform_filter(m, win)
    ok = den >= min_far
    ref = np.where(ok, num / np.maximum(den, 1e-6), np.nan)
    return ref, ok


def falloff(resid, dist, valid, dmax=140):
    prof = []
    for d in range(1, dmax + 1):
        s = (dist >= d) & (dist < d + 1) & valid
        if s.sum() >= 300:
            prof.append((d, float(np.median(resid[s])), int(s.sum())))
    return prof


def main():
    out = {}
    g = tifffile.imread(SCRATCH / "s31-bee3.tif")[Y0:Y0 + H, X0:X0 + W, 1
                                                  ].astype(np.float32)
    lo, hi = float(np.percentile(g, 1)), float(np.percentile(g, 99))
    med = float(np.median(g))
    span = max(hi - lo, 1.0) * 0.35
    q = span / 127.0
    print(f"=== operand ===\n  crop {g.shape}, one output code {q:.1f} DN")

    subj = ndimage.binary_opening(
        ndimage.binary_closing(g < med - span, np.ones((5, 5))), np.ones((3, 3)))
    print(f"  subject {100*subj.mean():.1f}% of crop")

    results = {}
    for tag, mask in (("REAL", subj), ("C-FAR", subj[::-1, ::-1].copy())):
        dist = ndimage.distance_transform_edt(~mask)
        far = (dist >= FARFIELD_D) & ~subj
        ref, ok = local_reference(g, far, WIN, MIN_FAR)
        valid = ok & ~subj & np.isfinite(ref)
        resid = g - ref
        prof = falloff(resid, dist, valid)
        tail = [v for d, v, _ in prof if d >= FARFIELD_D]
        base = float(np.median(tail)) if tail else 0.0
        inner = [(d, v) for d, v, _ in prof if 2 <= d <= 60]
        pd, pv = max(inner, key=lambda t: t[1])
        amp = pv - base
        results[tag] = {"profile": prof, "base": base, "peak_d": pd,
                        "peak": pv, "amp": amp,
                        "far_px": int(far.sum()),
                        "ref_sd": float(np.nanstd(resid[far & valid]))}
        print(f"\n--- {tag}: far field {100*far.mean():.1f}% of crop,"
              f" local reference window {WIN} px")
        print(f"  residual sd on the far field {results[tag]['ref_sd']:.1f} DN"
              f"   (86's global quadratic: 1736.3 DN)")
        print(f"  {'d':>4} {'residual DN':>13} {'n':>8}")
        for d, v, n in prof:
            if d in (1, 2, 3, 5, 8, 12, 18, 25, 35, 50, 70, 100, 140):
                print(f"  {d:4d} {v:+13.1f} {n:8d}")
        print(f"  baseline {base:+.1f} DN;  peak {pv:+.1f} DN at d={pd} px")
        print(f"  AMPLITUDE {amp:+.0f} DN = {amp/q:+.1f} output codes"
              f" = {100*amp/65535:.2f}% of full scale")

    amp = results["REAL"]["amp"]
    ctl = results["C-FAR"]["amp"]
    print(f"\n=== B11 ===")
    print(f"  real   {amp:+.0f} DN")
    print(f"  C-FAR  {ctl:+.0f} DN  (rotated mask, must be small)")
    print(f"  ratio  {amp/max(abs(ctl),1e-9):.2f}x")
    b11 = ("the veil is a LARGE feature; 'a few DN' is wrong"
           if amp >= B11_LARGE_CODES * q else
           "'a few DN' is right" if amp <= B11_FEW_DN else "INTERMEDIATE")
    print(f"  bar: large means >= {B11_LARGE_CODES*q:.0f} DN"
          f" ({B11_LARGE_CODES:.0f} output codes)")
    print(f"  B11: {b11}")
    print(f"  in an 8-bit sRGB viewer the render's {amp:.0f} DN is"
          f" {amp/257.0:.1f} of 255 codes -- plainly visible, not invisible")
    out["amp_dn"] = amp
    out["amp_codes"] = amp / q
    out["amp_pct_fullscale"] = 100 * amp / 65535
    out["amp_8bit_codes"] = amp / 257.0
    out["control_amp_dn"] = ctl
    out["peak_d"] = results["REAL"]["peak_d"]
    out["ref_sd"] = results["REAL"]["ref_sd"]
    out["B11"] = b11
    out["profile"] = results["REAL"]["profile"]
    out["control_profile"] = results["C-FAR"]["profile"]

    dist = ndimage.distance_transform_edt(~subj)
    far = (dist >= FARFIELD_D) & ~subj
    ref, ok = local_reference(g, far, WIN, MIN_FAR)
    resid = np.where(ok & ~subj, g - ref, 0.0)
    sc = np.clip(resid / (2.0 * abs(amp)) * 127.0 + 127.0, 0, 255).astype(np.uint8)
    rgb = np.dstack([sc] * 3)
    rgb[subj] = (0, 90, 160)
    Image.fromarray(rgb).save(SCRATCH / "VEIL-RESIDUAL.png")
    print(f"  wrote {SCRATCH / 'VEIL-RESIDUAL.png'}"
          f"  (residual vs local background, +/-{2*abs(amp):.0f} DN,"
          f" subject in blue)")

    DATA.mkdir(exist_ok=True)
    (DATA / "90-veil.json").write_text(json.dumps(out, indent=1, default=float),
                                       encoding="utf-8")
    print(f"wrote {DATA / '90-veil.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
