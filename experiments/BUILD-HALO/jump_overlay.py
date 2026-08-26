"""Are the extreme election-index jumps spatially coincident with the rim?

BUILD-CHROMA found adjacent-pixel index jumps of up to 191 frames in a
299-frame bracket, with a median of 0.000 -- a thin tail nobody had looked at.
ORCH asked one question and asked for it as a picture: do those jumps overlay
the silhouette, or are they scattered?

THE CIRCULARITY THIS AVOIDS.  `depth_profile.depth_mask` segments on the local
standard deviation of the election map, and a large adjacent-pixel jump IS
large local SD.  Binning the jump field on that mask would be binning a
statistic on itself, and it would manufacture exactly the coincidence being
looked for.  So the silhouette here comes from `f221` -- a single frame
rendered with STREHL_ONLY_FRAME, which has NO ELECTION IN IT AT ALL.  Its
subject outline is pure optics and is independent of the election map by
construction.  The election-derived mask is drawn on the picture too, but only
as a second opinion, never as the binning map.

WHAT A NULL LOOKS LIKE.  The tail is thin, so "jumps exist near the edge" is
not a finding -- edges are where everything happens.  The number that matters
is ENRICHMENT: the rate of extreme jumps in a band, divided by the rate over
the whole background.  1.0x is no coincidence at all.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

TRADE = Path(r"C:\dev\strehl-out\TRADE")
VEIL = Path(r"C:\dev\strehl-out\VEIL")
OUT = Path(r"C:\dev\strehl-out\JUMP")
SUBJ = "flower-bud-with-background-fern-cpl"
SUPPORT = 14


def luma(p):
    a = tifffile.imread(str(p))
    if a.dtype == np.uint16:
        a = a.astype(np.float64) / 65535.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def jump_field(e):
    """Max absolute index difference to the 4-neighbours, per pixel."""
    j = np.zeros_like(e, dtype=np.int32)
    for ax in (0, 1):
        d = np.abs(np.diff(e.astype(np.int32), axis=ax))
        pad = [(0, 0), (0, 0)]
        pad[ax] = (0, 1)
        j = np.maximum(j, np.pad(d, pad))
        pad[ax] = (1, 0)
        j = np.maximum(j, np.pad(d, pad))
    return j


def optics_silhouette(ref):
    """Subject outline from a NO-ELECTION frame. Independent of the election."""
    # flower-bud is a dark subject on bright ground, so Otsu-free: split at the
    # midpoint of the robust range, then keep large components only.
    lo, hi = np.percentile(ref, [2, 98])
    m = ref < (lo + hi) / 2.0
    m = ndimage.binary_closing(m, np.ones((9, 9)))
    m = ndimage.binary_opening(m, np.ones((9, 9)))
    lbl, n = ndimage.label(m)
    if n == 0:
        sys.exit("no subject found in the reference frame")
    sizes = ndimage.sum(m, lbl, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s > 0.01 * m.size]
    if not keep:
        keep = [int(np.argmax(sizes)) + 1]
    return ndimage.binary_fill_holes(np.isin(lbl, keep))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    e = tifffile.imread(str(VEIL / f"{SUBJ}-election.tif"))
    if e.ndim == 3:
        e = e[..., 0]
    ref = luma(TRADE / f"{SUBJ}-f221.tif")
    rend = luma(TRADE / f"{SUBJ}-off.tif")
    assert e.shape == ref.shape, f"grid mismatch {e.shape} vs {ref.shape}"

    j = jump_field(e)
    print(f"election map {e.shape}  index range {e.min()}..{e.max()}")
    print("\nadjacent-pixel index jump, whole plane")
    for q in (50, 90, 99, 99.9, 99.99):
        print(f"  p{q:<6} {np.percentile(j, q):>8.1f}")
    print(f"  max     {j.max():>8.1f}")

    m = optics_silhouette(ref)
    d = ndimage.distance_transform_edt(~m)
    print(f"\noptics silhouette (from f221, no election): {m.mean():.1%} of frame")

    # THRESHOLD FROM THE DATA, NOT CHOSEN. A fixed cut would let the enrichment
    # be tuned; the 99.9th percentile of the plane fixes the population size at
    # 0.1% by construction, so only its LOCATION is free to vary.
    thr = float(np.percentile(j, 99.9))
    extreme = (j >= thr) & ~m
    base = extreme.sum() / max((~m).sum(), 1)
    print(f"extreme = jump >= p99.9 = {thr:.0f} frames   "
          f"{int(extreme.sum()):,} px in background   base rate {base:.4%}")

    print(f"\n  {'band (px)':>12} {'n bg':>12} {'extreme':>10} {'rate':>9} "
          f"{'enrichment':>11}")
    print("  " + "-" * 60)
    edges = [1, 6, 12, 20, 28, 40, 56, 78, 108, 150, 208, 288, 400, 600]
    for a, b in zip(edges[:-1], edges[1:]):
        sel = (d >= a) & (d < b) & ~m
        n = int(sel.sum())
        if n < 2000:
            continue
        r = extreme[sel].sum() / n
        mark = "  <-- window support" if a <= SUPPORT < b else ""
        print(f"  {a:>5}-{b:<6} {n:>12,} {int(extreme[sel].sum()):>10,} "
              f"{r:>8.4%} {r / base if base else 0:>10.2f}x{mark}")
    print("  " + "-" * 60)

    near = (d >= 1) & (d < 20) & ~m
    far = (d > 300) & ~m
    en = (extreme[near].mean() / base) if base else 0
    print(f"\n  near band 1-20 px enrichment : {en:.2f}x")
    print(f"  far  band >300 px enrichment : "
          f"{(extreme[far].mean() / base) if base else 0:.2f}x")

    # IS THE INDEX FIELD BEING AVERAGED? ORCH's mechanism requires that a
    # smoother lands boundary pixels BETWEEN the two depths. The regulariser is
    # a box on the FOCUS field, not on the index field, so the elected index is
    # always an argmax some frame actually attained -- but that is a reading of
    # the source, and the map can say whether it is true.
    k_bg = int(np.median(e[far])) if far.sum() else -1
    k_fg = int(np.median(e[m]))
    lo, hi = sorted((k_fg, k_bg))
    if hi - lo > 20:
        inside = ((e[near] > lo + 0.2 * (hi - lo)) & (e[near] < hi - 0.2 * (hi - lo))).mean()
        print(f"\n  subject elects {k_fg}, far background elects {k_bg}")
        print(f"  near-band pixels electing the MIDDLE 60% between them: {inside:.1%}")
        print("  (an averaged index field would pile up here; an argmax cannot)")

    # THE PICTURE
    g = np.clip((rend - np.percentile(rend, 1)) /
                (np.percentile(rend, 99) - np.percentile(rend, 1)), 0, 1)
    rgb = np.stack([g, g, g], -1)
    outline = ndimage.binary_dilation(m, np.ones((3, 3))) & ~m
    rgb[ndimage.binary_dilation(extreme, np.ones((3, 3)))] = [1.0, 0.15, 0.15]
    rgb[outline] = [0.1, 1.0, 0.4]
    h, w = rend.shape
    img = Image.fromarray((rgb * 255).astype(np.uint8))
    img.resize((1400, int(h * 1400 / w)), Image.LANCZOS).save(OUT / "JUMP-overlay.png")
    # A crop at full resolution: a 1400 px downscale of a 1 px feature is a lie.
    ys, xs = np.where(outline)
    cy, cx = int(np.median(ys)), int(np.median(xs))
    y0, x0 = max(0, cy - 400), max(0, cx - 400)
    Image.fromarray((rgb[y0:y0 + 800, x0:x0 + 800] * 255).astype(np.uint8)).save(
        OUT / "JUMP-crop100.png")
    for p in (OUT / "JUMP-overlay.png", OUT / "JUMP-crop100.png"):
        assert p.read_bytes()[:4] == b"\x89PNG"
        print(f"  wrote {p}")


if __name__ == "__main__":
    main()
