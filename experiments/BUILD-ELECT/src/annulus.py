"""Look at the coffee-bean placebo motion of section 14.4 as a picture.

Section 14.4 reported that on the pre-registered negative control `coffee-bean`,
the blend arm introduces profile structure in the 47-93 px band that the control
does not have, 1.17% against 0.07% at d=93.  I reported that number and said in
the same breath that I had never looked at it.  This is the looking.

The question is not "is the number right" -- it was measured twice.  The question
is what it is made of, and there are three candidates:

  * real structure the blend adds, coherent over the annulus;
  * mask noise -- `coffee-bean`'s mask is 59.62% of the frame in 2115 components,
    so a "distance from the silhouette" of 93 px is an average over a great many
    unrelated silhouettes and a bin can be dominated by a handful of them;
  * a few localised sites that dominate a thin bin.

Those look identical in a radial profile and completely different in a picture,
which is the whole point.

Everything here is printed before any verdict, including the per-bin sample
counts, because a bin with few samples and a bin with a real signal produce the
same row otherwise.

    python annulus.py <control.tif> <blend.tif> [--out <png>]

The mask is always taken from the control arm: the mask is drawn by brightness,
so letting each arm draw its own moves the coordinate origin between arms and
measures the mask instead of the image.
"""

import pathlib
import sys

import numpy as np
from scipy import ndimage

import ringprofile as rp

LO, HI = 47, 93          # the band section 14.4 reported
CROPS = 4                # adversarial sites to show
CROP = 128               # 1:1 crop size, px


def annulus_bins(lum, signed, lo, hi):
    """Per-1px-bin mean and count in the outward annulus [lo, hi]."""
    rows = []
    for d in range(lo, hi + 1):
        sel = (signed >= d) & (signed < d + 1)
        n = int(sel.sum())
        rows.append((d, n, float(lum[sel].mean()) if n else float("nan")))
    return rows


def site_diff(ctl, bl, signed, lo, hi):
    """Where in the frame the two arms differ inside the annulus.

    Smoothed so that a single hot pixel cannot name a site, and masked to the
    annulus so that the far field and the subject cannot contribute.
    """
    band = (signed >= lo) & (signed <= hi)
    d = (bl - ctl) * band
    # normalise by the local count so a thin sliver of annulus is not favoured
    num = ndimage.uniform_filter(d, size=CROP)
    den = ndimage.uniform_filter(band.astype(np.float64), size=CROP)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(den > 0.25, num / np.maximum(den, 1e-9), 0.0)
    return m, band


def pick_sites(m, k, sep):
    """Top-k local maxima of |m|, separated by at least `sep` px."""
    work = np.abs(m).copy()
    out = []
    for _ in range(k):
        if not np.isfinite(work).any() or work.max() <= 0:
            break
        y, x = np.unravel_index(int(np.argmax(work)), work.shape)
        out.append((int(y), int(x), float(m[y, x])))
        y0, y1 = max(0, y - sep), min(work.shape[0], y + sep)
        x0, x1 = max(0, x - sep), min(work.shape[1], x + sep)
        work[y0:y1, x0:x1] = 0.0
    return out


def main():
    argv = sys.argv[1:]
    out = "annulus.png"
    if "--out" in argv:
        i = argv.index("--out")
        out = argv[i + 1]
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 2

    ctl_p, bl_p = args
    ctl = rp.load_luma(ctl_p)
    bl = rp.load_luma(bl_p)
    if ctl.shape != bl.shape:
        print(f"  shapes differ: {ctl.shape} vs {bl.shape} -- not an A/B")
        return 2

    mask, thr, kept, found = rp.subject_mask(ctl)
    signed = rp.signed_distance(mask)

    print(f"control : {pathlib.Path(ctl_p).name}")
    print(f"blend   : {pathlib.Path(bl_p).name}")
    print(f"  mask from the control: thr={thr:.0f}, "
          f"{mask.mean() * 100:.2f}% of frame, "
          f"{kept} component(s) kept of {found} found by the threshold")
    print(f"  frame {ctl.shape[1]}x{ctl.shape[0]}")
    print()

    # --- the whole band, row by row, counts included -------------------------
    rc = annulus_bins(ctl, signed, LO, HI)
    rb = annulus_bins(bl, signed, LO, HI)
    print(f"  the {LO}-{HI} px band, per 1 px bin, both arms, linear DN")
    print(f"  {'d':>4} {'n px':>9} {'control':>10} {'blend':>10} "
          f"{'blend-ctl':>10} {'as % ctl':>9}")
    for (d, n, c), (_, _, b) in zip(rc, rb):
        if not n:
            print(f"  {d:>4} {n:>9} {'--':>10} {'--':>10} {'--':>10} {'--':>9}")
            continue
        print(f"  {d:>4} {n:>9} {c:>10.1f} {b:>10.1f} {b - c:>10.1f} "
              f"{(b - c) / c * 100:>8.2f}%")
    print()

    cnt = np.array([n for _, n, _ in rc], float)
    print(f"  bin population over the band: min {cnt.min():.0f}, "
          f"median {np.median(cnt):.0f}, max {cnt.max():.0f}, "
          f"ratio max/min {cnt.max() / max(cnt.min(), 1):.1f}x")
    dif = np.array([b - c for (_, n, c), (_, _, b) in zip(rc, rb) if n])
    print(f"  blend-ctl over the band: mean {dif.mean():+.1f} DN, "
          f"sd {dif.std():.1f} DN, min {dif.min():+.1f}, max {dif.max():+.1f}")
    print()

    # --- how is the difference distributed in space? -------------------------
    # Concentration MUST be measured on the raw per-pixel difference. An earlier
    # version measured it on the 128 px smoothed field used for site-picking,
    # which destroys concentration by construction and so could only ever report
    # "diffuse". Caught by V-ELECT-15.
    m, band = site_diff(ctl, bl, signed, LO, HI)
    raw = (bl - ctl)[band]
    raw = raw[np.isfinite(raw)]
    print(f"  annulus covers {int(band.sum())} px "
          f"({band.mean() * 100:.2f}% of frame)")
    if raw.size:
        a = np.abs(raw)
        order = np.sort(a)[::-1]
        tot = order.sum()
        for frac in (0.01, 0.05, 0.10, 0.25):
            k = max(1, int(frac * order.size))
            print(f"  top {frac * 100:>5.1f}% of annulus px carry "
                  f"{order[:k].sum() / max(tot, 1e-9) * 100:>6.2f}% of |blend-ctl|"
                  f"   (uniform would be {frac * 100:.1f}%)")
        print(f"  |blend-ctl| per pixel: median {np.median(a):.1f} DN, "
              f"p95 {np.percentile(a, 95):.1f} DN, max {a.max():.1f} DN")
        print(f"  blend > control at {float((raw > 0).mean()) * 100:.2f}% "
              f"of annulus pixels")
    print()

    sites = pick_sites(m, CROPS, CROP)
    print(f"  {CROPS} largest-|blend-ctl| sites, smoothed over {CROP} px. "
          f"NOTE these are selected on the very difference they illustrate, so "
          f"they are circular as evidence; and the smoothing means the site "
          f"CENTRE need not lie in the band. Its signed distance is printed so "
          f"that cannot be assumed. (Both caught by V-ELECT-15.)")
    for i, (y, x, v) in enumerate(sites, 1):
        print(f"    site {i}: (y={y}, x={x})  signed d={signed[y, x]:+7.1f} px"
              f"  {'IN' if LO <= signed[y, x] <= HI else 'OUTSIDE'} the "
              f"{LO}-{HI} band  mean blend-ctl {v:+.1f} DN")
    print()

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:                                # pragma: no cover
        print(f"  no picture: {exc}")
        return 0

    n = len(sites)
    fig, ax = plt.subplots(3, max(n, 2), figsize=(4.2 * max(n, 2), 12.6))
    lim = float(np.percentile(np.abs(m[band]), 99.5)) if band.any() else 1.0
    ax[0, 0].imshow(np.where(band, m, np.nan), cmap="coolwarm",
                    vmin=-lim, vmax=lim)
    ax[0, 0].set_title(f"blend - control inside {LO}-{HI} px\n"
                       f"+-{lim:.0f} DN", fontsize=9)
    ax[0, 1].imshow(band, cmap="gray")
    ax[0, 1].set_title(f"the {LO}-{HI} px annulus itself\n"
                       f"{kept} mask component kept of {found}", fontsize=9)
    for j in range(2, max(n, 2)):
        ax[0, j].axis("off")
    for a_ in ax[0]:
        a_.set_xticks([])
        a_.set_yticks([])

    for j, (y, x, v) in enumerate(sites):
        y0, x0 = max(0, y - CROP // 2), max(0, x - CROP // 2)
        cc = ctl[y0:y0 + CROP, x0:x0 + CROP]
        bb = bl[y0:y0 + CROP, x0:x0 + CROP]
        both = np.concatenate([cc.ravel(), bb.ravel()])
        v0, v1 = np.percentile(both, 1), np.percentile(both, 99)
        ax[1, j].imshow(cc, cmap="gray", vmin=v0, vmax=v1)
        ax[1, j].set_title(f"control  site {j + 1}  ({y},{x})\n"
                           f"mean {cc.mean():.0f} DN", fontsize=9)
        ax[2, j].imshow(bb, cmap="gray", vmin=v0, vmax=v1)
        ax[2, j].set_title(f"blend  {v:+.0f} DN in band\n"
                           f"mean {bb.mean():.0f} DN", fontsize=9)
    for j in range(n, max(n, 2)):
        ax[1, j].axis("off")
        ax[2, j].axis("off")
    for row in ax[1:]:
        for a_ in row:
            a_.set_xticks([])
            a_.set_yticks([])

    fig.suptitle("14.4: the coffee-bean placebo motion, looked at. "
                 "Both arms one binary, both linear, control's mask, "
                 "each crop pair on one stretch.", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
