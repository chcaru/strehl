"""M107b R5: resolve the selection confound in R1's R2 arm.

THE CONFOUND. R1 selected edge pixels with a per-image 99th-percentile gradient
threshold. The render is sharper than the LibRaw control, so its top-1% sits
where IT is sharpest -- and its edge count collapsed to <500 in the outer
annuli while the control still had 13832-40188 there. So the per-annulus excess
was comparing DIFFERENT pixel populations, and "excess rises with radius" could
be a selection effect: as radius grows, only the very highest-contrast render
edges survive the global cut, and higher contrast carries more chroma.

THE FIX. Two changes, either of which alone would weaken the confound:
  1. ABSOLUTE common threshold: take the gradient cut from the CONTROL's 99th
     percentile and apply that same absolute value to both images. Both arms
     then mean "pixels with gradient above g*", not "each image's own top 1%".
  2. GRADIENT-NORMALISED chroma: report mean(chroma/grad). Fringe width scales
     with displacement and fringe amplitude scales with edge contrast, so
     dividing by grad removes the contrast term that the confound acts through.

Counts for BOTH arms are printed per annulus so the reader can see coverage
rather than trust it.

BARS, REGISTERED BEFORE THE NUMBERS ARE SEEN
  R5a  With the common absolute threshold AND gradient normalisation, does the
       excess still rise with radius?
         RISING (outer/inner >= 1.50) -> the radial term survives the confound
              and R1's R2 finding stands.
         FLAT ([0.80,1.25]) -> R1's R2 was a selection artefact. I withdraw it.
         Anything else -> report as unresolved, do not pick.
  R5b  COVERAGE GATE: any annulus where EITHER arm has < 2000 selected pixels is
       reported as sparse and excluded from the trend. R1 used 500, which was
       too permissive given what the counts turned out to look like.
  R5c  CONTROL: the same gradient-normalised statistic on FLAT pixels. Lateral
       CA and election error both act only on edges. If the flat arm shows the
       same radial rise, the effect is colour shading and neither mechanism.
"""
import glob
import sys

import numpy as np
import tifffile

N_ANN = 6
MIN_N = 2000


def load(path):
    a = tifffile.imread(path)
    if a.dtype == np.uint16:
        a = a.astype(np.float32) / 65535.0
    elif a.dtype == np.uint8:
        a = a.astype(np.float32) / 255.0
    else:
        a = a.astype(np.float32)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    return a[..., :3]


def fields(path):
    img = load(path)
    y = 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]
    chroma = np.maximum(np.abs(img[..., 0] - y), np.abs(img[..., 2] - y)).astype(np.float32)
    del img
    gy, gx = np.gradient(y)
    grad = np.hypot(gx, gy).astype(np.float32)
    del y, gy, gx
    h, w = grad.shape
    yy = (np.arange(h, dtype=np.float32) - (h - 1) / 2.0)[:, None]
    xx = (np.arange(w, dtype=np.float32) - (w - 1) / 2.0)[None, :]
    r = np.sqrt(yy * yy + xx * xx) / float(np.hypot((h - 1) / 2.0, (w - 1) / 2.0))
    return chroma, grad, r.astype(np.float32), (h, w)


def annuli(chroma, grad, r, thr, normalise):
    sel = grad >= thr
    edges = np.linspace(0.0, 1.0, N_ANN + 1)
    out = []
    for i in range(N_ANN):
        m = sel & (r >= edges[i]) & (r < edges[i + 1])
        n = int(m.sum())
        if n < 1:
            out.append((n, float("nan")))
            continue
        v = chroma[m] / grad[m] if normalise else chroma[m]
        out.append((n, float(v.mean())))
    return out


def trend(pairs_a, pairs_b):
    """outer/inner of the excess, using only annuli where BOTH arms are dense."""
    vals = []
    for (na, va), (nb, vb) in zip(pairs_a, pairs_b):
        ok = na >= MIN_N and nb >= MIN_N and np.isfinite(va) and np.isfinite(vb) and vb > 0
        vals.append(va / vb if ok else float("nan"))
    dense = [v for v in vals if np.isfinite(v)]
    t = dense[-1] / dense[0] if len(dense) >= 3 and dense[0] > 0 else float("nan")
    return vals, t


def verdict(x):
    if not np.isfinite(x):
        return "INDETERMINATE"
    if x >= 1.50:
        return "RISING"
    if x <= 0.80:
        return "FALLING"
    if x <= 1.25:
        return "FLAT -- R1's R2 withdrawn"
    return "UNRESOLVED (1.25-1.50)"


def main():
    tn = r"C:\dev\strehl-out\ORCH-thennow"
    scenes = {
        "lavendar": (rf"{tn}\lavendar-HEAD-8f46f04.tif",
                     rf"{tn}\CONTROL-singleframe-lavendar-cpl.tif"),
        "marker": (rf"{tn}\marker-HEAD-8f46f04.tif",
                   glob.glob(rf"{tn}\CONTROL-singleframe-dry-erase-marker*.tif")[0]),
    }
    for name, (rp, cp) in scenes.items():
        print("=" * 74)
        print(f"SCENE {name}")
        rc, rg, rr, rshape = fields(rp)
        cc, cg, cr, cshape = fields(cp)
        print(f"  render {rshape[1]}x{rshape[0]}   control {cshape[1]}x{cshape[0]}"
              f"{'   (SHAPES DIFFER -- no pixel correspondence)' if rshape != cshape else ''}")

        thr = float(np.percentile(cg, 99.0))
        r_own = float(np.percentile(rg, 99.0))
        print(f"  common absolute gradient threshold g* = {thr:.6f} (control p99)")
        print(f"  render's own p99 would have been        {r_own:.6f}  "
              f"({r_own / thr:.2f}x the control's -- this ratio IS the confound)")

        for norm in (False, True):
            tag = "chroma/grad" if norm else "chroma     "
            ra = annuli(rc, rg, rr, thr, norm)
            ca = annuli(cc, cg, cr, thr, norm)
            vals, t = trend(ra, ca)
            print(f"  --- {tag} , common g* ---")
            print(f"  {'annulus':>11s} {'n_render':>10s} {'n_control':>10s} "
                  f"{'render':>11s} {'control':>11s} {'excess':>9s}")
            for i in range(N_ANN):
                lo, hi = i / N_ANN, (i + 1) / N_ANN
                sparse = "" if (ra[i][0] >= MIN_N and ca[i][0] >= MIN_N) else "  SPARSE"
                ex = "nan" if not np.isfinite(vals[i]) else f"{vals[i]:8.2f}"
                print(f"  {lo:.2f}-{hi:.2f} {ra[i][0]:10d} {ca[i][0]:10d} "
                      f"{ra[i][1]:11.6f} {ca[i][1]:11.6f} {ex}{sparse}")
            label = "R5a" if norm else "R5a(unnormalised)"
            print(f"  {label} outer/inner = {t:.3f}  -> {verdict(t)}")

        # R5c control on flat pixels, gradient-normalised
        flat_thr = float(np.percentile(cg, 50.0))
        rf_ = annuli(rc, -rg, rr, -flat_thr, False)
        cf_ = annuli(cc, -cg, cr, -flat_thr, False)
        vals, t = trend(rf_, cf_)
        print(f"  R5c FLAT-pixel excess per annulus: "
              + ", ".join("nan" if not np.isfinite(x) else f"{x:.2f}" for x in vals))
        print(f"  R5c outer/inner = {t:.3f}  -> {verdict(t)}"
              "   (if RISING, the edge result is shading, not an edge defect)")
        del rc, rg, rr, cc, cg, cr
    return 0


if __name__ == "__main__":
    sys.exit(main())
