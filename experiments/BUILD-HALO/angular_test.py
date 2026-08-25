"""Is lavender's dark surround a symmetric halo, or a directional shadow?

ORCH named this discriminator himself: a cast shadow is DIRECTIONAL, offset
toward one side by the light; a selection halo traces the ENTIRE silhouette
including the up-light side.  So bin the near-edge background by ANGLE around
the subject and look at the spread.

  symmetric  -> every angular sector is depressed by about the same amount
  shadow     -> a sector is strongly depressed and the opposite sector is clean

The mask is built from the ALL-IN-FOCUS stacked render, not from a median over
the focus ladder.  The median is smeared by the very defocus under study, which
is what produced an unusable mask on the first attempt.

Output is a table AND a picture, because a directionality claim should be
visible, not merely tabulated.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

OUT = Path(r"C:\dev\strehl-out\VEIL")
NEAR = (20, 140)     # the band ORCH calls "the veiled surround"
FAR = 420
NBINS = 24


def luma(p):
    a = tifffile.imread(str(p))
    if a.dtype == np.uint16:
        a = a.astype(np.float64) / 65535.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def mask_from_stack(L):
    """Bright subject on a mid-grey ground: threshold, then keep the big blob."""
    lo, hi = np.percentile(L, [2, 98])
    best = None
    for q in (0.35, 0.45, 0.55, 0.65):
        t = lo + q * (hi - lo)
        m = L > t
        if m.mean() > 0.5:
            m = ~m
        m = ndimage.binary_closing(m, np.ones((11, 11)))
        m = ndimage.binary_opening(m, np.ones((11, 11)))
        lbl, n = ndimage.label(m)
        if n == 0:
            continue
        sizes = ndimage.sum(m, lbl, range(1, n + 1))
        m = ndimage.binary_fill_holes(lbl == (int(np.argmax(sizes)) + 1))
        f = m.mean()
        if 0.08 < f < 0.55:
            best = m if best is None else best
    if best is None:
        sys.exit("could not segment the subject")
    return best


def main():
    stack_p = OUT / "lavendar-cpl-stacked.tif"
    if not stack_p.exists():
        sys.exit(f"missing {stack_p}")
    L = luma(stack_p)
    m = mask_from_stack(L)

    d = ndimage.distance_transform_edt(~m)
    far_sel = d > FAR
    if far_sel.sum() < 50000:
        sys.exit("no far background -- subject too large or FAR too big")
    far = float(np.median(L[far_sel]))
    subj = float(np.median(L[m]))
    print(f"mask {m.mean():.1%}   subject {subj:.4f}   far bg {far:.4f}   "
          f"-> {'BRIGHT' if subj > far else 'DARK'} subject on "
          f"{'darker' if subj > far else 'brighter'} ground")

    cy, cx = ndimage.center_of_mass(m)
    yy, xx = np.indices(L.shape)
    ang = (np.degrees(np.arctan2(yy - cy, xx - cx)) + 360.0) % 360.0

    band = (d >= NEAR[0]) & (d < NEAR[1])
    print(f"\nnear-edge band {NEAR[0]}-{NEAR[1]}px, binned by angle from the "
          f"subject centroid ({int(cx)},{int(cy)})")
    print("value is band median / far-background median; <1 means DARKER than far background\n")
    print(f"  {'angle':>10} {'n':>9} {'rel':>9}   (0 deg = +x / right, 90 = down)")
    print("  " + "-" * 52)

    vals, edges = [], np.linspace(0, 360, NBINS + 1)
    for a, b in zip(edges[:-1], edges[1:]):
        sel = band & (ang >= a) & (ang < b)
        n = int(sel.sum())
        if n < 500:
            vals.append(np.nan)
            print(f"  {a:>4.0f}-{b:<5.0f} {n:>9} {'--':>9}")
            continue
        v = float(np.median(L[sel])) / far
        vals.append(v)
        bar = "#" * max(0, int(round((1.0 - v) * 120)))
        print(f"  {a:>4.0f}-{b:<5.0f} {n:>9} {v:>9.4f}   {bar}")

    v = np.array(vals, dtype=float)
    ok = np.isfinite(v)
    lo_, hi_ = float(np.nanmin(v)), float(np.nanmax(v))
    depth_lo, depth_hi = 1.0 - hi_, 1.0 - lo_
    print("  " + "-" * 52)
    print(f"\n  cleanest sector: {hi_:.4f} of far bg  (depression {depth_lo:+.4f})")
    print(f"  darkest  sector: {lo_:.4f} of far bg  (depression {depth_hi:+.4f})")
    if depth_hi > 1e-6:
        aniso = depth_hi / max(depth_lo, 1e-6)
        print(f"  anisotropy (darkest depression / cleanest depression): {aniso:.1f}x")
        print("\n  A SYMMETRIC halo predicts anisotropy ~1: every sector depressed alike.")
        print("  A DIRECTIONAL shadow predicts one sector strongly depressed and the")
        print("  opposite sector near 1.0.")
        if depth_lo <= 0.005 and depth_hi > 0.02:
            print("\n  -> DIRECTIONAL. At least one sector is CLEAN; this is not a halo")
            print("     tracing the whole silhouette.")
        elif aniso > 3:
            print("\n  -> STRONGLY ANISOTROPIC -- dominated by a directional term.")
        else:
            print("\n  -> broadly SYMMETRIC -- consistent with a halo, not a cast shadow.")

    # the picture
    g = np.clip((L - np.percentile(L, 1)) / (np.percentile(L, 99) - np.percentile(L, 1)), 0, 1)
    rgb = np.stack([g, g, g], -1)
    rel = np.full(L.shape, np.nan)
    for i, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
        if ok[i]:
            rel[band & (ang >= a) & (ang < b)] = v[i]
    dev = np.clip((rel - 1.0) / 0.25, -1, 1)
    sel = np.isfinite(dev)
    rgb[sel & (dev < 0)] = np.stack([
        rgb[..., 0], rgb[..., 1] * 0.3, rgb[..., 2] * 0.3], -1)[sel & (dev < 0)]
    rgb[sel & (dev >= 0)] = np.stack([
        rgb[..., 0] * 0.3, rgb[..., 1] * 0.3, rgb[..., 2]], -1)[sel & (dev >= 0)]
    edge = ndimage.binary_dilation(m, np.ones((3, 3))) & ~m
    rgb[edge] = [0.1, 1.0, 0.1]
    h, w = L.shape
    img = Image.fromarray((rgb * 255).astype(np.uint8)).resize((1500, int(h * 1500 / w)), Image.LANCZOS)
    p = OUT / "ANGULAR-lavendar-cpl.png"
    img.save(p)
    assert p.read_bytes()[:4] == b"\x89PNG"
    print(f"\n  wrote {p}  (RED = darker than far bg, BLUE = brighter, green = silhouette)")


if __name__ == "__main__":
    main()
