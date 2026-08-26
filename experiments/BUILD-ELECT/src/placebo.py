"""What the 14.4 placebo motion on `coffee-bean` is actually made of.

`annulus.py` showed the blend is +5657 DN brighter than the control right across
the 47-93 px band, diffusely, with a uniformly populated distance axis.  So 14.4
is neither mask noise nor a few hot sites.  But it left two questions open and
both have to be answered before the motion can be characterised:

  1.  **Is the brightening global or local?**  A whole-frame gain or offset is a
      calibration difference between arms and says nothing about the near
      backdrop.  Only a brightening that is *confined* to the near backdrop is a
      change in the veiling term.  Measured by comparing the same statistic in
      the deep interior, the annulus, and the far field.

  2.  **Is the blend smoother there, or only brighter?**  In `annulus.py`'s
      montage each crop pair shares one stretch, and the blend sits ~8000 DN
      higher in it, so the blend is compressed toward white *by construction*
      and looks flatter whether or not it is.  This report has already made that
      exact error once, in 13.5, where a "-23.1% REAL SOFTENING" turned out to be
      a region legitimately darkening 20710 DN to 1417 DN.  So contrast here is
      measured level-invariantly, as local Weber contrast, and the crops are
      re-rendered each normalised by its own mean so that the stretch cannot
      manufacture flatness.

Everything is printed before any verdict, and the zone levels are printed in
absolute DN, not as ratios, because an additive difference is invisible in a
ratio.

    python placebo.py <control.tif> <blend.tif> [--out <png>]
"""

import pathlib
import sys

import numpy as np
from scipy import ndimage

import ringprofile as rp

BAND = (47, 93)          # the 14.4 band
FAR = (300, 600)         # far field
CROP = 128
CROPS = 4
WEBER = 9                # local window for Weber contrast, px


def zone_stats(lum, signed, sel, name):
    v = lum[sel]
    return name, int(v.size), float(v.mean()), float(np.median(v))


def weber(lum, sel):
    """Local Weber contrast: mean over the region of (local sd / local mean).

    Scale-free, so a brighter arm cannot score higher for being brighter.  An
    additive offset does move it, which is why absolute levels are reported
    separately above.

    Two things this statistic does NOT do, both found by V-ELECT-15:
      * `mean(sd/mean) * mean(mean)` is not `mean(sd)`, so it cannot be
        multiplied back up to recover an absolute sd. `local_sd` does that.
      * a monotone ramp inside the window produces sd with no texture present
        at all, so on a veiled backdrop this reads the veil gradient rather
        than structure. `detrended_sd` removes the local plane first.
    """
    m = ndimage.uniform_filter(lum, size=WEBER)
    m2 = ndimage.uniform_filter(lum * lum, size=WEBER)
    sd = np.sqrt(np.maximum(m2 - m * m, 0.0))
    with np.errstate(invalid="ignore", divide="ignore"):
        w = np.where(m > 1.0, sd / np.maximum(m, 1e-9), np.nan)
    v = w[sel]
    v = v[np.isfinite(v)]
    return float(v.mean()), float(np.median(v)), int(v.size)


def local_sd(lum, sel, detrend=False):
    """Mean absolute local sd in DN over the region, optionally ramp-immune.

    With detrend=True the local plane (fitted from the local mean gradient over
    the same window) is removed before the sd, so a smooth veil ramp inside the
    window contributes nothing and only structure survives.
    """
    x = lum.astype(np.float64)
    m = ndimage.uniform_filter(x, size=WEBER)
    m2 = ndimage.uniform_filter(x * x, size=WEBER)
    var = np.maximum(m2 - m * m, 0.0)
    if detrend:
        # variance a linear ramp of slope g contributes over a w-wide box is
        # g^2 * (w^2 - 1) / 12 per axis; subtract it off both axes
        gy, gx = np.gradient(m)
        k = (WEBER * WEBER - 1.0) / 12.0
        var = np.maximum(var - k * (gy * gy + gx * gx), 0.0)
    v = np.sqrt(var)[sel]
    v = v[np.isfinite(v)]
    return float(v.mean())


def saturated(img_path):
    """Fraction of pixels with any channel pinned at the container ceiling."""
    import tifffile
    a = tifffile.imread(img_path)
    return (a == 65535).any(axis=2)


def main():
    argv = sys.argv[1:]
    out = "placebo.png"
    if "--out" in argv:
        i = argv.index("--out")
        out = argv[i + 1]
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 2

    ctl = rp.load_luma(args[0])
    bl = rp.load_luma(args[1])
    mask, thr, kept, found = rp.subject_mask(ctl)
    signed = rp.signed_distance(mask)
    sat = saturated(args[0]) | saturated(args[1])

    print(f"control : {pathlib.Path(args[0]).name}")
    print(f"blend   : {pathlib.Path(args[1]).name}")
    print(f"  mask from the control: thr={thr:.0f}, "
          f"{mask.mean() * 100:.2f}% of frame, "
          f"{kept} component(s) kept of {found} found by the threshold")
    print()

    zones = [
        ("deep interior (d <= -60)", signed <= -60),
        ("interior collar (-30..-5)", (signed >= -30) & (signed <= -5)),
        (f"the 14.4 band ({BAND[0]}-{BAND[1]})",
         (signed >= BAND[0]) & (signed <= BAND[1])),
        ("near backdrop (1..20)", (signed >= 1) & (signed <= 20)),
        ("mid backdrop (120..250)", (signed >= 120) & (signed <= 250)),
        (f"far field ({FAR[0]}-{FAR[1]})",
         (signed >= FAR[0]) & (signed <= FAR[1])),
    ]

    # --- 1. global or local? absolute DN, per the DN requirement --------------
    print("  zone levels, absolute linear DN, one binary, both arms linear")
    print(f"  {'zone':<26} {'n px':>10} {'control':>10} {'blend':>10} "
          f"{'diff DN':>9} {'gain':>7}")
    diffs = {}
    for name, sel in zones:
        n = int(sel.sum())
        if not n:
            print(f"  {name:<26} {n:>10} {'--':>10} {'--':>10} "
                  f"{'--':>9} {'--':>7}")
            continue
        c, b = float(ctl[sel].mean()), float(bl[sel].mean())
        diffs[name] = (c, b, n)
        print(f"  {name:<26} {n:>10} {c:>10.1f} {b:>10.1f} "
              f"{b - c:>+9.1f} {b / max(c, 1e-9):>7.4f}")
    print()

    if "far field (300-600)" in diffs and f"the 14.4 band ({BAND[0]}-{BAND[1]})" in diffs:
        fc, fb, _ = diffs["far field (300-600)"]
        bc, bb, _ = diffs[f"the 14.4 band ({BAND[0]}-{BAND[1]})"]
        print(f"  if the brightening were a global offset, the far field would "
              f"carry it too:")
        print(f"    far field  blend-control = {fb - fc:+.1f} DN")
        print(f"    14.4 band  blend-control = {bb - bc:+.1f} DN")
        if abs(fb - fc) > 1.0:
            print(f"    the band's excess over the far field's = "
                  f"{(bb - bc) / (fb - fc):.2f}x")
        else:
            print(f"    the far field is unmoved, so the brightening is LOCAL")
        print(f"  if it were a global gain, the gains would match: "
              f"far {fb / max(fc, 1e-9):.4f} vs band {bb / max(bc, 1e-9):.4f}")
    print()

    # --- 2. smoother, or only brighter? --------------------------------------
    # The chain matters more than any single number. Naive Weber is inflated by
    # BOTH the rising mean and the veil ramp inside the window, and both arms'
    # highlights can be against the container ceiling. Each column below removes
    # one of those. Read the last column.
    print(f"  contrast, four ways. sat% is pixels with any channel == 65535 in "
          f"EITHER arm; the 'clean' columns exclude them.")
    print(f"  {'zone':<26} {'sat%':>7} {'W chg':>8} {'sd chg':>8} "
          f"{'clean sd':>9} {'detrended':>10}")
    for name, sel in zones:
        if not sel.any():
            continue
        wc, _, _ = weber(ctl, sel)
        wb, _, _ = weber(bl, sel)
        sc, sb = local_sd(ctl, sel), local_sd(bl, sel)
        keep = sel & ~sat
        if keep.sum() < 1000:
            print(f"  {name:<26} {sel[sat].size and float(sat[sel].mean()) * 100:>6.2f}% "
                  f"{'--':>8} {'--':>8} {'--':>9} {'--':>10}")
            continue
        kc, kb = local_sd(ctl, keep), local_sd(bl, keep)
        dc = local_sd(ctl, keep, detrend=True)
        db = local_sd(bl, keep, detrend=True)
        print(f"  {name:<26} {float(sat[sel].mean()) * 100:>6.2f}% "
              f"{(wb - wc) / max(wc, 1e-9) * 100:>+7.2f}% "
              f"{(sb - sc) / max(sc, 1e-9) * 100:>+7.2f}% "
              f"{(kb - kc) / max(kc, 1e-9) * 100:>+8.2f}% "
              f"{(db - dc) / max(dc, 1e-9) * 100:>+9.2f}%")
    print()
    print(f"  absolute local sd in DN (not a ratio), saturation-excluded, "
          f"ramp-detrended")
    print(f"  {'zone':<26} {'n kept':>10} {'control':>10} {'blend':>10}")
    for name, sel in zones:
        keep = sel & ~sat
        if keep.sum() < 1000:
            continue
        print(f"  {name:<26} {int(keep.sum()):>10} "
              f"{local_sd(ctl, keep, detrend=True):>10.1f} "
              f"{local_sd(bl, keep, detrend=True):>10.1f}")
    print()

    # --- the picture, each crop on its own normalisation ----------------------
    band = (signed >= BAND[0]) & (signed <= BAND[1])
    d = (bl - ctl) * band
    num = ndimage.uniform_filter(d, size=CROP)
    den = ndimage.uniform_filter(band.astype(np.float64), size=CROP)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(den > 0.25, num / np.maximum(den, 1e-9), 0.0)

    work = np.abs(m).copy()
    sites = []
    for _ in range(CROPS):
        if work.max() <= 0:
            break
        y, x = np.unravel_index(int(np.argmax(work)), work.shape)
        sites.append((int(y), int(x), float(m[y, x])))
        y0, y1 = max(0, y - CROP), min(work.shape[0], y + CROP)
        x0, x1 = max(0, x - CROP), min(work.shape[1], x + CROP)
        work[y0:y1, x0:x1] = 0.0

    print("  per-crop Weber contrast, each crop measured on itself")
    print(f"  {'site':<22} {'ctl mean':>10} {'bl mean':>10} "
          f"{'ctl W':>9} {'bl W':>9} {'change':>9}")
    pairs = []
    for i, (y, x, v) in enumerate(sites, 1):
        y0, x0 = max(0, y - CROP // 2), max(0, x - CROP // 2)
        cc = ctl[y0:y0 + CROP, x0:x0 + CROP]
        bb = bl[y0:y0 + CROP, x0:x0 + CROP]
        full = np.ones(cc.shape, bool)
        wc, _, _ = weber(cc, full)
        wb, _, _ = weber(bb, full)
        pairs.append((cc, bb, y, x, v, wc, wb))
        print(f"  site {i} ({y},{x})".ljust(24)
              + f"{cc.mean():>10.0f} {bb.mean():>10.0f} "
                f"{wc:>9.5f} {wb:>9.5f} "
                f"{(wb - wc) / max(wc, 1e-9) * 100:>+8.2f}%")
    print()

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:                                # pragma: no cover
        print(f"  no picture: {exc}")
        return 0

    n = max(len(pairs), 1)
    fig, ax = plt.subplots(2, n, figsize=(4.2 * n, 8.8), squeeze=False)
    for j, (cc, bb, y, x, v, wc, wb) in enumerate(pairs):
        # each crop normalised by its OWN mean, then a common relative stretch,
        # so brightness cannot manufacture flatness in either direction
        cn, bn = cc / cc.mean(), bb / bb.mean()
        lo = min(np.percentile(cn, 1), np.percentile(bn, 1))
        hi = max(np.percentile(cn, 99), np.percentile(bn, 99))
        ax[0, j].imshow(cn, cmap="gray", vmin=lo, vmax=hi)
        ax[0, j].set_title(f"control  ({y},{x})\n"
                           f"mean {cc.mean():.0f} DN   W={wc:.4f}", fontsize=9)
        ax[1, j].imshow(bn, cmap="gray", vmin=lo, vmax=hi)
        ax[1, j].set_title(f"blend  {v:+.0f} DN\n"
                           f"mean {bb.mean():.0f} DN   W={wb:.4f}", fontsize=9)
    for row in ax:
        for a_ in row:
            a_.set_xticks([])
            a_.set_yticks([])
    fig.suptitle("14.4 placebo motion, level-invariant: each crop divided by "
                 "its own mean, then both on one relative stretch. "
                 "Brightness cannot flatten either arm here.", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
