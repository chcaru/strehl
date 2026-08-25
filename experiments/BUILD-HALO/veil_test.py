"""Does the near-edge background change brightness as focus sweeps?

THE LOGIC.  A veil is a property of the FRAME: if the defocused subject spills
its light onto nearby background, that background must get brighter (or darker)
as the subject goes out of focus, and must be clean in the frame where the
subject is sharp.  Illumination gradients, contact shadows and estimator
overshoot are all frame-INVARIANT in the background.  So sweeping focus over
single frames -- with no election anywhere in the pipeline -- separates ORCH's
veiling mechanism from every alternative, using nothing but mean luminance.

DISCIPLINE.
  * ONE mask, built once, used for every frame.  V-HALO killed a previous
    result of mine because the edge set was re-detected per arm, so the arms
    were not paired.
  * Every frame is normalised by its OWN far-background level before profiles
    are compared, so a per-frame exposure difference cannot masquerade as a
    veil.  The test is then a pure SHAPE test.
  * No gradient, high-pass or edge-energy statistic anywhere.  Those have
    produced a confident wrong reading three times on this artifact.
  * Signed quantities are reported raw.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

OUT = Path(r"C:\dev\strehl-out\VEIL")
FRAMES = [0, 50, 100, 150, 200, 250, 298]
FAR = 400          # px: "far background", assumed unveiled
EDGE_BAND = (2, 16)  # px: the rim, set by SOBEL_RADIUS + WINDOW_RADIUS


def luma(path):
    a = tifffile.imread(str(path))
    if a.dtype == np.uint16:
        a = a.astype(np.float64) / 65535.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def subject_mask(subject):
    """Frozen silhouette, built from ONE image and verified before use.

    Built from the frame where the subject is sharpest is tempting but
    circular; instead use the median across the ladder, which is dominated by
    the subject wherever the subject sits and by background elsewhere.
    """
    stack = [luma(OUT / f"{subject}-f{f:03d}.tif") for f in FRAMES]
    med = np.median(np.stack(stack), axis=0)

    lo, hi = np.percentile(med, [1, 99])
    t = 0.5 * (lo + hi)
    # Which side is the subject?  The subject is the MINORITY class here (it
    # does not fill the frame), so take whichever side is smaller.
    a = med > t
    m = a if a.mean() < 0.5 else ~a

    m = ndimage.binary_closing(m, np.ones((9, 9)))
    m = ndimage.binary_opening(m, np.ones((9, 9)))
    lbl, n = ndimage.label(m)
    if n == 0:
        sys.exit(f"{subject}: no subject found")
    sizes = ndimage.sum(m, lbl, range(1, n + 1))
    m = lbl == (int(np.argmax(sizes)) + 1)
    m = ndimage.binary_fill_holes(m)

    frac = m.mean()
    if not (0.01 < frac < 0.75):
        sys.exit(f"{subject}: mask covers {frac:.1%} -- implausible, refusing")
    return m, med


def run(subject):
    print(f"\n{'='*72}\n{subject}\n{'='*72}")
    mask, med = subject_mask(subject)
    dist = ndimage.distance_transform_edt(~mask)

    subj_lvl = float(np.median(med[mask]))
    far_lvl = float(np.median(med[dist > FAR]))
    polarity = "BRIGHT subject on darker bg" if subj_lvl > far_lvl else "DARK subject on brighter bg"
    print(f"mask covers {mask.mean():.1%};  subject median {subj_lvl:.4f}, "
          f"far bg median {far_lvl:.4f}  -> {polarity}")

    edges = [2, 6, 10, 16, 24, 36, 52, 76, 110, 160, 230, 330, FAR]
    profiles = {}
    for f in FRAMES:
        L = luma(OUT / f"{subject}-f{f:03d}.tif")
        far = np.median(L[dist > FAR])
        if not np.isfinite(far) or far <= 0:
            sys.exit(f"{subject} f{f}: no usable far background")
        prof = []
        for a, b in zip(edges[:-1], edges[1:]):
            band = (dist >= a) & (dist < b)
            prof.append(float(np.median(L[band])) / far)   # normalised per frame
        profiles[f] = np.array(prof)

    centres = [0.5 * (a + b) for a, b in zip(edges[:-1], edges[1:])]
    print("\nbackground luminance / far-background, by distance from silhouette")
    print("  (1.000 = same as far background; a veil makes the near bands move "
          "toward the subject's own brightness)\n")
    hdr = "  dist |" + "".join(f"{c:>8.0f}" for c in centres)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for f in FRAMES:
        print(f"  f{f:<4d}|" + "".join(f"{v:>8.4f}" for v in profiles[f]))

    spread = np.array([max(profiles[f][i] for f in FRAMES) - min(profiles[f][i] for f in FRAMES)
                       for i in range(len(centres))])
    print("  " + "-" * (len(hdr) - 2))
    print("  spred|" + "".join(f"{v:>8.4f}" for v in spread))

    near = spread[0]
    farsp = spread[-1]
    print(f"\n  frame-to-frame spread at the rim ({centres[0]:.0f}px): {near:.4f}")
    print(f"  frame-to-frame spread far out   ({centres[-1]:.0f}px): {farsp:.4f}")
    ratio = near / farsp if farsp > 0 else float("inf")
    print(f"  ratio: {ratio:.2f}x")
    print("\n  VEIL PREDICTS: near-edge background depends strongly on frame")
    print("                 (ratio >> 1, frames fan out approaching the edge).")
    print("  ALTERNATIVES : illumination / contact shadow / overshoot are all")
    print("                 frame-invariant in the background (ratio ~ 1).")
    verdict = "consistent with a FRAME-DEPENDENT VEIL" if ratio > 3 else \
              "NO frame dependence -- veiling NOT supported"
    print(f"  -> {verdict}")
    return subject, polarity, ratio, verdict


if __name__ == "__main__":
    subs = sys.argv[1:] or ["lavendar-cpl", "flower-bud-with-background-fern-cpl"]
    rows = [run(s) for s in subs]
    print(f"\n\n{'='*72}\nSUMMARY\n{'='*72}")
    for s, pol, r, v in rows:
        print(f"  {s:<40} {pol:<28} {r:>6.2f}x  {v}")
