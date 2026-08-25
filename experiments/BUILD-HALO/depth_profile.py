"""Silhouette from DEPTH, then the radial decay ORCH asked me to measure.

WHY DEPTH.  Two luminance-threshold silhouettes have already failed on these
subjects: a white flower on mid grey defeats a global threshold, and a
median-over-focus image is smeared by the very defocus under study.  The
engine's election map is the pass-one winner field -- the 0-based frame index
each pixel elects -- so it is a DEPTH ordering and cannot be fooled by
brightness at all.

The subject is segmented by DEPTH COHERENCE rather than by frame index,
because the backdrop in this corpus is featureless: it is dead ground, its
election is noise spanning the bracket, and noise is exactly what a local
spread statistic sees.  A real object has a resolvable depth and elects
coherently.

UNITS -- the trap, and the correction.  I first assumed the election map was on
a half-resolution plane grid and doubled the predicted support to 28 px.  THAT
WAS WRONG AND IT IS WORTH SAYING SO HERE, because a doubled prediction happens
to agree with the ring this build was chasing and would have confirmed the
wrong mechanism.  Measured, the map is 3520x2344 -- the SAME grid as the
render -- so window support is SOBEL_RADIUS + WINDOW_RADIUS = 14 px in output
pixels.  `run` therefore measures the ratio (`L.shape[0] / m_plane.shape[0]`)
and rescales, rather than assuming either value; do not reintroduce a constant
here.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

OUT = Path(r"C:\dev\strehl-out\VEIL")
SOBEL_RADIUS, WINDOW_RADIUS = 1, 13
SUPPORT = SOBEL_RADIUS + WINDOW_RADIUS   # in ELECTION-MAP pixels; rescaled below


def luma(p):
    a = tifffile.imread(str(p))
    if a.dtype == np.uint16:
        a = a.astype(np.float64) / 65535.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def depth_mask(elect):
    """Coherent-depth region, on the plane grid."""
    e = elect.astype(np.float64)
    k = 9
    mean = ndimage.uniform_filter(e, k)
    var = ndimage.uniform_filter(e * e, k) - mean * mean
    sd = np.sqrt(np.clip(var, 0, None))

    # Dead ground's election spans the bracket; a real object's does not.
    t = np.percentile(sd, 55)
    m = sd < t
    m = ndimage.binary_closing(m, np.ones((9, 9)))
    m = ndimage.binary_opening(m, np.ones((9, 9)))
    lbl, n = ndimage.label(m)
    if n == 0:
        sys.exit("no coherent-depth region found")
    sizes = ndimage.sum(m, lbl, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s > 0.02 * m.size]
    if not keep:
        keep = [int(np.argmax(sizes)) + 1]
    m = np.isin(lbl, keep)
    m = ndimage.binary_fill_holes(m)
    return m, sd


def run(subject):
    emap = OUT / f"{subject}-election.tif"
    cands = [OUT / f"{subject}-elect-render.tif", OUT / f"{subject}-stacked.tif"]
    rend = next((c for c in cands if c.exists()), None)
    if not emap.exists() or rend is None:
        sys.exit(f"missing inputs for {subject} (need election map + a merged render)")

    elect = tifffile.imread(str(emap))
    if elect.ndim == 3:
        elect = elect[..., 0]
    L = luma(rend)
    print(f"\n{'='*74}\n{subject}\n{'='*74}")
    print(f"election map {elect.shape} (plane grid)   render {L.shape} (sensor grid)")
    valid = elect[elect != 65535]
    print(f"elected frame index: min {valid.min()} max {valid.max()} "
          f"median {int(np.median(valid))}")

    m_plane, sd = depth_mask(elect)
    # The election map's grid is whatever the engine wrote; do NOT assume it is
    # half the render. Measure the ratio and rescale the support radius with it,
    # so the predicted and measured radii are quoted in ONE grid.
    scale = L.shape[0] / m_plane.shape[0]
    if abs(scale - round(scale)) > 1e-6:
        sys.exit(f"non-integer grid ratio {scale}")
    scale = int(round(scale))
    support_px = SUPPORT * scale
    print(f"grid ratio render/election = {scale}x  ->  window support = "
          f"{support_px} px in the rendered image")
    m = m_plane if scale == 1 else np.repeat(np.repeat(m_plane, scale, 0), scale, 1)
    if m.shape != L.shape:
        m = m[:L.shape[0], :L.shape[1]]
        if m.shape != L.shape:
            pad = [(0, L.shape[i] - m.shape[i]) for i in range(2)]
            m = np.pad(m, pad, mode="edge")

    d = ndimage.distance_transform_edt(~m)
    far_sel = d > 500
    if far_sel.sum() < 30000:
        sys.exit(f"{subject}: no far background beyond 500 px")
    far = float(np.median(L[far_sel]))
    subj = float(np.median(L[m]))
    print(f"depth mask covers {m.mean():.1%}   subject {subj:.4f}   "
          f"far bg {far:.4f}   -> {'BRIGHT' if subj > far else 'DARK'} subject")

    edges = [1, 6, 12, 20, 28, 40, 56, 78, 108, 150, 208, 288, 400, 500]
    print(f"\n  background luminance / far background, by distance from the "
          f"DEPTH silhouette (px)")
    print(f"  window support = {support_px} px "
          f"({SOBEL_RADIUS}+{WINDOW_RADIUS} plane px)\n")
    print(f"  {'band':>12} {'n':>10} {'rel':>9}  {'dev':>9}")
    print("  " + "-" * 46)
    rows = []
    for a, b in zip(edges[:-1], edges[1:]):
        # ~m is essential: distance_transform_edt returns 0 INSIDE the mask, so
        # without it the first band swallows the whole subject and reports the
        # subject's own brightness as if it were background.
        sel = (d >= a) & (d < b) & ~m
        n = int(sel.sum())
        if n < 400:
            continue
        v = float(np.median(L[sel])) / far
        rows.append((0.5 * (a + b), v, n))
        marker = "  <-- window support" if a <= support_px < b else ""
        print(f"  {a:>5}-{b:<6} {n:>10} {v:>9.4f}  {v-1:>+9.4f}{marker}")
    print("  " + "-" * 46)

    dev = np.array([abs(v - 1.0) for _, v, _ in rows])
    cen = np.array([c for c, _, _ in rows])
    peak = float(dev.max())
    if peak > 0:
        # first distance at which the deviation has decayed below 10% of peak
        below = np.where(dev < 0.10 * peak)[0]
        decay = float(cen[below[0]]) if len(below) else float("nan")
        print(f"\n  peak deviation {peak:+.4f} at {cen[int(np.argmax(dev))]:.0f} px")
        print(f"  decays to <10% of peak by {decay:.0f} px")
        print(f"  window-support prediction: {support_px} px")
        if np.isfinite(decay):
            print(f"  ratio measured/predicted: {decay / support_px:.2f}x")

    # picture: silhouette + the support radius, so the claim is visible
    g = np.clip((L - np.percentile(L, 1)) / (np.percentile(L, 99) - np.percentile(L, 1)), 0, 1)
    rgb = np.stack([g, g, g], -1)
    ring = (d >= support_px - 1) & (d <= support_px + 1)
    outline = ndimage.binary_dilation(m, np.ones((3, 3))) & ~m
    rgb[ring] = [0.1, 0.5, 1.0]
    rgb[outline] = [0.1, 1.0, 0.1]
    h, w = L.shape
    img = Image.fromarray((rgb * 255).astype(np.uint8)).resize((1500, int(h * 1500 / w)), Image.LANCZOS)
    p = OUT / f"DEPTHMASK-{subject}.png"
    img.save(p)
    assert p.read_bytes()[:4] == b"\x89PNG"
    print(f"  wrote {p.name}  (green = depth silhouette, blue = window support)")


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["lavendar-cpl", "flower-bud-with-background-fern-cpl"]):
        run(s)
