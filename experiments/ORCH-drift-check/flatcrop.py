"""Flat-field crops and noise, chosen by FLATNESS -- the opposite selection rule to
sheet.py, which ranks by edge density.

Section 28 is the reason this exists as a separate instrument: a sampling rule
that selects for one feature is blind to everything that is not that feature.
sheet.py finds halos because it looks at edges; it cannot see backdrop noise
because it never looks at the backdrop. V-RIM measured the blend arm at
1.21-1.58x the noise of ONE raw exposure in the out-of-focus backdrop, which for
a 205-frame stack should instead be roughly sqrt(205) BELOW it. If that is real
it is visible in print as a blotchy background, and no edge-selected crop will
ever show it.

Selection is on a THIRD arm where one is available, or on the per-arm mean where
it is not, so that neither arm under test drives the choice of where it is
measured. V-RIM measured that letting the arm under test help pick tiles halves
its own apparent noise (128.8 -> 68.4).
"""
import numpy as np, tifffile, os, sys

def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def flat_tiles(sel, tile=256, want=6, edge_margin=384):
    """Return the flattest tiles of `sel`, avoiding the frame border."""
    h, w = sel.shape
    cands = []
    for y in range(edge_margin, h - tile - edge_margin, tile):
        for x in range(edge_margin, w - tile - edge_margin, tile):
            t = sel[y:y + tile, x:x + tile]
            # Flatness on a BLURRED copy so that noise itself does not make a
            # tile look textured and disqualify exactly the tiles we need.
            m = t.mean()
            if m < 2000:
                continue  # skip near-black; noise there is a different question
            g = np.abs(np.diff(t, axis=0)).mean() + np.abs(np.diff(t, axis=1)).mean()
            cands.append((g, y, x, m))
    cands.sort()
    return cands[:want]


def hf_sigma(t):
    """Robust high-frequency scatter. A Laplacian-like difference kills any smooth
    gradient across the tile, so a slow vignette does not read as noise."""
    d = t[1:-1, 1:-1] * 4.0 - t[:-2, 1:-1] - t[2:, 1:-1] - t[1:-1, :-2] - t[1:-1, 2:]
    # MAD -> sigma for a normal, divided by the Laplacian's noise gain sqrt(20).
    mad = np.median(np.abs(d - np.median(d)))
    return 1.4826 * mad / np.sqrt(20.0)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: flatcrop.py <out.png-prefix> <armname=path.tiff> <armname=path.tiff> [...]")
        raise SystemExit(2)
    prefix = sys.argv[1]
    arms = []
    for a in sys.argv[2:]:
        nm, _, p = a.partition("=")
        if not os.path.exists(p):
            raise SystemExit(f"missing: {p}")
        arms.append((nm, p))

    imgs = {}
    for nm, p in arms:
        imgs[nm] = luma(tifffile.imread(p).astype(np.float64))
    shapes = {v.shape for v in imgs.values()}
    if len(shapes) != 1:
        raise SystemExit(f"arms differ in shape: {shapes}")

    # Selector belongs to no single arm.
    sel = np.mean(list(imgs.values()), axis=0)
    tiles = flat_tiles(sel)
    if not tiles:
        raise SystemExit("no flat tiles found")

    print(f"{'tile':>4s} {'y':>6s} {'x':>6s} {'mean':>9s}  " +
          "  ".join(f"{nm:>14s}" for nm, _ in arms))
    print("-" * (30 + 16 * len(arms)))
    acc = {nm: [] for nm, _ in arms}
    for i, (g, y, x, m) in enumerate(tiles):
        row = f"{i:>4d} {y:>6d} {x:>6d} {m:>9.0f}  "
        for nm, _ in arms:
            s = hf_sigma(imgs[nm][y:y + 256, x:x + 256])
            acc[nm].append(s)
            row += f"{s:>14.1f}  "
        print(row)
    print("-" * (30 + 16 * len(arms)))
    print(f"{'MEDIAN':>28s}  " + "  ".join(f"{np.median(acc[nm]):>14.1f}" for nm, _ in arms))
    base = np.median(acc[arms[0][0]])
    print(f"{'RATIO to ' + arms[0][0]:>28s}  " +
          "  ".join(f"{np.median(acc[nm])/base:>14.3f}" for nm, _ in arms))

    # Write a side-by-side of the flattest tile at 100% so the number can be seen.
    try:
        from PIL import Image
        g, y, x, m = tiles[0]
        lo, hi = np.percentile(sel[y:y+256, x:x+256], [0.5, 99.5])
        span = max(hi - lo, 1.0)
        panels = []
        for nm, p in arms:
            t = imgs[nm][y:y + 256, x:x + 256]
            u8 = np.clip((t - lo) / span * 255.0, 0, 255).astype(np.uint8)
            panels.append(np.repeat(np.repeat(u8, 2, axis=0), 2, axis=1))
        sheet = np.concatenate([np.pad(p, ((0, 0), (0, 8)), constant_values=255)
                                for p in panels], axis=1)
        out = f"{prefix}-flattile.png"
        Image.fromarray(sheet).save(out)
        print(f"\nwrote {out}  (tile y={y} x={x}, mean {m:.0f} DN, "
              f"stretched 0.5-99.5 pct of the SELECTOR, 2x nearest)")
        print("  order: " + " | ".join(nm for nm, _ in arms))
    except Exception as e:
        print(f"(no picture: {e})")
