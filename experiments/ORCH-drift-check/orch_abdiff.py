"""Side-by-side 1:1 adjudication of two renders of the same subject.

Every fix landing tonight -- the lateral-CA re-fit, the dust map, the soft
admission gate -- is scored by a statistic in its own lane. This is the
instrument that asks the different question: LOOK at the places the two renders
actually disagree, at native resolution, under one shared transform, and decide
whether the change is an improvement, a regression, or invisible.

Three design choices, each of which is a correction of a mistake made tonight:

1. DEFAULT ZOOM IS 1. `orch_zoom.py` renders at 3x nearest-neighbour, and I read
   its rendering as block structure in the data -- built a Bayer-cell hypothesis
   on it, briefed a lane on it, and was refuted by a measurement of modal run
   length (1 px, phase near-uniform mod 2/4/8/16/32). Integer zoom is honest
   about pixels and dishonest about morphology. Zoom is available but must be
   asked for, and the montage labels it when used.

2. ONE SHARED TRANSFORM ACROSS BOTH IMAGES, derived from A alone. Autoscaling
   each pane to its own percentile makes a brightness change invisible and
   manufactures contrast differences that are not there. The transform is
   printed so it can be quoted.

3. SITES ARE CHOSEN BY THE DIFFERENCE, NOT BY THE CONTENT. A crop rule keyed to
   edges or texture will land on the same features regardless of what changed,
   which is how a survey misses a regional defect. Sites are the top-K local
   maxima of a box-filtered absolute difference, forced apart by a separation
   radius so K sites are not K views of one site.

Null: A against A must report zero differing pixels and refuse to emit a
montage, because a differ that draws something for identical inputs cannot be
trusted to mean anything when it draws something for different ones.
"""
import argparse
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw


def load(path):
    arr = tifffile.imread(path)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise SystemExit("REFUSED: %s is %r, expected (H, W, >=3)" % (path, arr.shape))
    return arr[:, :, :3].astype(np.float64)


def box(a, r):
    """Separable running-sum box filter, O(1) per pixel in the radius."""
    if r <= 0:
        return a
    pad = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(pad, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)), mode="constant")
    h, w = a.shape
    k = 2 * r + 1
    s = (c[k:k + h, k:k + w] - c[0:h, k:k + w]
         - c[k:k + h, 0:w] + c[0:h, 0:w])
    return s / float(k * k)


def pick_sites(diff, count, half, sep):
    """Top-`count` local maxima of a smoothed difference, forced `sep` apart.

    The raw argmax is refined to the centroid of the maximal plateau. This is
    not cosmetic. A difference that is flat over a region -- which is what any
    uniform change looks like after a box filter -- produces a plateau of
    exactly equal values, and `np.argmax` returns its FIRST element in raster
    order, not its centre. Commissioning this tool with a uniform disc of radius
    60 under a box of radius 8 put the reported site 51 px above the plant, a
    systematic (disc - box) offset that looks exactly like a localisation error
    and is not one. Left unrefined, every crop would sit off the top edge of the
    thing it is meant to show.
    """
    score = box(diff, 8).copy()
    h, w = score.shape
    score[:half, :] = -1.0
    score[h - half:, :] = -1.0
    score[:, :half] = -1.0
    score[:, w - half:] = -1.0

    sites = []
    for _ in range(count):
        idx = int(np.argmax(score))
        y, x = divmod(idx, w)
        peak = float(score[y, x])
        if peak <= 0:
            break

        # Centroid of the plateau, searched only in a window about the argmax so
        # a distant equal-valued region cannot drag the site off the feature.
        r = min(sep // 2, 400)
        wy0, wy1 = max(0, y - r), min(h, y + r)
        wx0, wx1 = max(0, x - r), min(w, x + r)
        win = score[wy0:wy1, wx0:wx1]
        plateau = win >= peak * (1.0 - 1e-9)
        ys, xs = np.nonzero(plateau)
        if ys.size:
            y = int(round(wy0 + ys.mean()))
            x = int(round(wx0 + xs.mean()))
            y = min(max(y, half), h - half - 1)
            x = min(max(x, half), w - half - 1)

        sites.append((y, x, peak))
        y0, y1 = max(0, y - sep), min(h, y + sep)
        x0, x1 = max(0, x - sep), min(w, x + sep)
        score[y0:y1, x0:x1] = -1.0
    return sites


def to8(patch, lo, hi):
    v = (patch - lo) / max(hi - lo, 1e-9)
    return np.clip(v, 0.0, 1.0) ** (1.0 / 2.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("out")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--sites", type=int, default=4)
    ap.add_argument("--size", type=int, default=420, help="crop edge in NATIVE px")
    ap.add_argument("--zoom", type=int, default=1,
                    help="integer nearest-neighbour zoom; 1 = native, and the "
                         "default is 1 on purpose (see module docstring)")
    ap.add_argument("--sep", type=int, default=900)
    args = ap.parse_args()

    a = load(args.a)
    b = load(args.b)
    if a.shape != b.shape:
        raise SystemExit("REFUSED: geometry differs, %r vs %r -- this tool "
                         "compares renders of the same subject, and a shape "
                         "mismatch means one of them is not what you think"
                         % (a.shape, b.shape))

    d = np.abs(a - b)
    dmax = float(d.max())
    ndiff = int((d.max(axis=2) > 0).sum())
    total = a.shape[0] * a.shape[1]
    print("A: %s" % args.a)
    print("B: %s" % args.b)
    print("shape                : %r" % (a.shape,))
    print("pixels differing     : %d of %d (%.6f%%)"
          % (ndiff, total, 100.0 * ndiff / total))
    print("max |A-B|            : %.1f DN" % dmax)
    for ci, cn in enumerate("RGB"):
        cd = d[:, :, ci]
        print("  %s differs on %8d px, max %8.1f DN, mean(nonzero) %8.2f"
              % (cn, int((cd > 0).sum()), float(cd.max()),
                 float(cd[cd > 0].mean()) if (cd > 0).any() else 0.0))

    if ndiff == 0:
        print()
        print("NULL: the two renders are bit-identical. No montage written -- "
              "a differ that draws something here could not be trusted to mean "
              "anything when it draws something elsewhere.")
        return 0

    lo = 0.0
    hi = float(np.percentile(a, 99.9))
    print("shared transform     : lo=%.1f hi=%.1f (99.9th pct of A), gamma 2.2" % (lo, hi))

    half = args.size // 2
    sites = pick_sites(d.max(axis=2), args.sites, half, args.sep)
    if not sites:
        raise SystemExit("REFUSED: %d differing pixels but no site survived the "
                         "border exclusion -- every difference is within %d px "
                         "of an edge, which is itself the finding"
                         % (ndiff, half))

    z = max(1, args.zoom)
    cw, ch = args.size * z, args.size * z
    gap, top = 12, 34
    sheet = Image.new("RGB", (cw * 3 + gap * 4, (ch + top) * len(sites) + gap),
                      (16, 16, 16))
    draw = ImageDraw.Draw(sheet)

    for row, (y, x, sc) in enumerate(sites):
        y0, x0 = y - half, x - half
        pa = a[y0:y0 + args.size, x0:x0 + args.size]
        pb = b[y0:y0 + args.size, x0:x0 + args.size]
        # Signed difference about mid grey, amplified by a stated factor so a
        # sub-DN change is visible without pretending it is large.
        amp = 8.0
        pd = np.clip(0.5 + (pb - pa) / max(hi, 1e-9) * amp, 0.0, 1.0)

        panes = [to8(pa, lo, hi), to8(pb, lo, hi), pd]
        names = [args.label_a, args.label_b, "(B-A) x%.0f about mid grey" % amp]
        for col, (pane, nm) in enumerate(zip(panes, names)):
            img = Image.fromarray((pane * 255.0 + 0.5).astype(np.uint8))
            if z > 1:
                img = img.resize((cw, ch), Image.NEAREST)
            px = gap + col * (cw + gap)
            py = gap + row * (ch + top) + top
            sheet.paste(img, (px, py))
            draw.text((px + 4, py - 22),
                      "%s   site y=%d x=%d   score %.1f DN%s"
                      % (nm, y, x, sc, "   ZOOM x%d NEAREST" % z if z > 1 else ""),
                      fill=(235, 235, 235))
        print("site %d: y=%d x=%d  mean|d| %.1f DN  max|d| %.1f DN"
              % (row, y, x, sc, float(np.abs(pb - pa).max())))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    sheet.save(args.out, quality=96)
    print()
    print("wrote %s  (%dx%d, %d site(s), zoom x%d)"
          % (args.out, sheet.width, sheet.height, len(sites), z))
    return 0


if __name__ == "__main__":
    sys.exit(main())
