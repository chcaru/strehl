"""THE DECISIVE TEST, now that the silhouette comes from depth.

A veil is a property of the FRAME.  If the near-edge background is veiled by
the defocused subject, its brightness must move as focus sweeps, and must be
cleanest in the frame where the subject is sharp.  Illumination, a cast shadow
and lens vignetting are all frame-INVARIANT in the background.

The mask is built ONCE from the election map (depth, not brightness) and shared
by every frame, so the arms are paired -- the failure that killed an earlier
dose-response here was re-detecting the edge set per arm.  Each frame is
normalised by its OWN far background, so a per-frame exposure difference cannot
masquerade as a veil; the comparison is then purely one of SHAPE.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
from depth_profile import OUT, SOBEL_RADIUS, WINDOW_RADIUS, depth_mask, luma  # noqa: E402

FRAMES = [0, 50, 100, 150, 200, 250, 298]
BANDS = [(1, 12), (12, 28), (28, 56), (56, 108), (108, 208), (208, 400)]
SUPPORT = SOBEL_RADIUS + WINDOW_RADIUS


def run(subject):
    emap = OUT / f"{subject}-election.tif"
    if not emap.exists():
        sys.exit(f"missing {emap}")
    elect = tifffile.imread(str(emap))
    if elect.ndim == 3:
        elect = elect[..., 0]
    m, _ = depth_mask(elect)
    d = ndimage.distance_transform_edt(~m)
    far_sel = (d > 500) & ~m

    print(f"\n{'='*78}\n{subject}   (depth silhouette, frozen across all frames)\n{'='*78}")
    print(f"mask {m.mean():.1%};  far-background reference = d>500px, "
          f"{far_sel.sum():,} px\n")

    hdr = "  frame |" + "".join(f"{f'{a}-{b}':>11}" for a, b in BANDS)
    print("  each cell = band median / that frame's OWN far background")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    table = {}
    for f in FRAMES:
        p = OUT / f"{subject}-f{f:03d}.tif"
        if not p.exists():
            sys.exit(f"missing ladder frame {p}")
        L = luma(p)
        far = float(np.median(L[far_sel]))
        row = []
        for a, b in BANDS:
            sel = (d >= a) & (d < b) & ~m
            row.append(float(np.median(L[sel])) / far)
        table[f] = np.array(row)
        print(f"  f{f:<5d}|" + "".join(f"{v:>11.4f}" for v in row))

    arr = np.stack([table[f] for f in FRAMES])
    spread = arr.max(0) - arr.min(0)
    spatial = float(np.nanmax(np.abs(arr.mean(0) - 1.0)))
    print("  " + "-" * (len(hdr) - 2))
    print("  spred |" + "".join(f"{v:>11.4f}" for v in spread))

    print(f"\n  largest frame-to-frame spread over any band : {spread.max():.4f}")
    print(f"  spatial depth of the artifact (mean profile) : {spatial:.4f}")
    ratio = spatial / spread.max() if spread.max() > 0 else float("inf")
    print(f"  spatial / frame-dependent                    : {ratio:.1f}x")

    print("\n  A DEFOCUS VEIL is frame-dependent by construction: the subject's")
    print("  spill changes as it goes in and out of focus, so the bands must")
    print("  fan out across frames and be cleanest where the subject is sharp.")
    print("  ILLUMINATION, a cast shadow and vignetting do not move with focus.")
    if ratio > 3:
        print(f"\n  -> The artifact is {ratio:.0f}x more SPATIAL than FRAME-DEPENDENT.")
        print("     It is mostly NOT a defocus veil: no choice of frame removes it,")
        print("     because every frame carries it.")
    else:
        print("\n  -> Substantial frame dependence: consistent with a defocus veil,")
        print("     and a selection policy can therefore reach it.")

    # Which frame is cleanest nearest the edge? A veil predicts this is the
    # frame where the subject is sharp, and that it is markedly cleaner.
    near = arr[:, 0]
    best = FRAMES[int(np.argmax(near))]
    print(f"\n  cleanest frame in the 1-12px band: f{best} at {near.max():.4f} "
          f"(worst f{FRAMES[int(np.argmin(near))]} at {near.min():.4f})")
    print(f"  best-case residual if selection could pick it everywhere: "
          f"{near.max()-1:+.4f}")
    print(f"  (a selection policy CANNOT do better than the best single frame)")


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["lavendar-cpl", "flower-bud-with-background-fern-cpl"]):
        run(s)
