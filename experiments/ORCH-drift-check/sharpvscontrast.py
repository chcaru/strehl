"""Separate sharpness from contrast across the delivered masters.

detailgallery.py ranks subjects by mean |laplacian| in linear DN. That statistic
conflates two different things:

  - how much fine structure the stack RESOLVED   (what we want to measure)
  - how much contrast the SUBJECT has            (a fact about the flower)

A white-on-white petal can be perfectly stacked and still score near the bottom,
because there is almost no signal to modulate. Ranking on the raw number and
concluding "the merge failed on flowers" is a subject-property misread as a
tool-property.

This computes both, in the same tile, from the same masters:

  raw   = mean |laplacian|                       (DN)
  norm  = mean |laplacian| / local RMS contrast  (dimensionless)

where local RMS contrast is the standard deviation of the tile after removing a
large-scale background (box mean over `BG`), so it measures the amplitude of
the structure actually present rather than the subject's overall brightness.

If the flowers are SHARP BUT LOW-CONTRAST, they rank low on raw and normally on
norm. If they are genuinely BLURRED, they rank low on both. That is the whole
experiment, and it discriminates the two in one pass.

CONTROL: a blurred copy of each tile must move `norm` DOWN. A normalisation that
divides out the very thing blur destroys would be inert, and an inert statistic
that happens to rank flowers higher would look exactly like a discovery.
"""
import sys
import pathlib
import numpy as np
import tifffile

TILE = 800
BG = 33


def boxmean(a, k):
    p = np.pad(a, k // 2, mode="reflect").astype(np.float64)
    c = np.cumsum(np.cumsum(p, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    s = c[k:k + h, k:k + w] - c[:h, k:k + w] - c[k:k + h, :w] + c[:h, :w]
    return s / (k * k)


def lap_mean(a):
    p = a.astype(np.float64)
    return float(np.abs(4 * p[1:-1, 1:-1] - p[:-2, 1:-1] - p[2:, 1:-1]
                        - p[1:-1, :-2] - p[1:-1, 2:]).mean())


def contrast(a):
    return float((a.astype(np.float64) - boxmean(a, BG)).std())


def blur3(a):
    return boxmean(a, 3)


def best_tile(g, tile, margin=64):
    h, w = g.shape
    lap = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
    step = max(tile // 2, 1)
    best = (-1.0, margin, margin)
    for y in range(margin, max(h - tile - margin, margin + 1), step):
        for x in range(margin, max(w - tile - margin, margin + 1), step):
            s = float(lap[y:y + tile, x:x + tile].mean())
            if s > best[0]:
                best = (s, y, x)
    return best


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    srcdir = pathlib.Path(sys.argv[1])
    masters = sorted(srcdir.glob("*.tiff"))
    if not masters:
        print(f"no .tiff in {srcdir}")
        return 2

    rows = []
    ctl_fail = []
    for i, m in enumerate(masters, 1):
        img = tifffile.imread(str(m))
        g = img[:, :, 1].astype(np.float32)
        _, y, x = best_tile(g, TILE)
        t = g[y:y + TILE, x:x + TILE]
        raw = lap_mean(t)
        con = contrast(t)
        norm = raw / max(con, 1e-9)
        # control: blurring must lower norm
        tb = blur3(t)
        nb = lap_mean(tb) / max(contrast(tb), 1e-9)
        if not nb < norm:
            ctl_fail.append((m.stem, norm, nb))
        rows.append((m.stem, raw, con, norm, nb))
        print(f"  [{i:2d}/{len(masters)}] {m.stem:<36} raw={raw:8.1f} contrast={con:8.1f} norm={norm:6.3f}")

    print()
    if ctl_fail:
        print("CONTROL FAILED -- blurring did not lower `norm` for:")
        for nm, a, b in ctl_fail:
            print(f"    {nm}: norm={a:.4f} blurred={b:.4f}")
        print("The statistic is not blur-monotone. Its ranking is uninterpretable.")
        return 1
    print(f"CONTROL PASSED: blurring lowered `norm` for all {len(rows)}/{len(rows)} subjects.")
    print("The statistic responds to blur, so a high value is evidence of resolved detail.")

    def show(title, key):
        print(f"\n{title}")
        print(f"  {'#':>2}  {'subject':<36}{'raw DN':>9}{'contrast':>10}{'norm':>8}")
        for r, (nm, raw, con, norm, _) in enumerate(sorted(rows, key=key, reverse=True), 1):
            flag = "  <- flower" if "flower" in nm or nm == "lavendar-cpl" else ""
            print(f"  {r:2d}  {nm:<36}{raw:9.1f}{con:10.1f}{norm:8.3f}{flag}")

    show("RANKED BY RAW DETAIL (what detailgallery.py used)", lambda r: r[1])
    show("RANKED BY DETAIL PER UNIT CONTRAST", lambda r: r[3])
    return 0


if __name__ == "__main__":
    sys.exit(main())
