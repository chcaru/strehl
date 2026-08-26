"""Does correcting the per-frame exposure drift remove the aura?

`aura_hull_raw.py` measured the bracket's single-frame arms spanning 3530 DN
(18.3%) in the far field, monotone with frame index, and the engine's own
photometric fit independently reports `gain span 1.2350` across 205 frames.
`main.rs` says of that term: "a gated average without this term is reading an
exposure change as a signal change" -- and `off` is the shipped default.

Section 22 measured the elected frame ramping smoothly with distance from the
subject, from frame 111 at the silhouette to frame 1 at d=400-500 px. Compose
the two and there is a mechanism for the aura that involves no veiling at all:

    a monotone exposure ramp across the bracket, sampled by a monotone election
    ramp across distance, paints the exposure drift onto the backdrop as a
    function of distance from the subject.

That predicts a dark aura of roughly the drift's own size, tracking the
silhouette, terminating where the election ramp terminates. It is a rival to
veiling and the two are separable by one flag.

This is a paired merge-vs-merge comparison, which section 19 bans for measuring
a halo AGAINST A REFERENCE -- a merge cannot tell you what a selector should
have done. It is used here for the one thing it is valid for: an A/B of one
flag, where both arms are the same estimator and only the flag differs. The
absolute halo numbers still come from the single-frame reference.

Referencing each arm to its own far field is legitimate HERE, where both arms
are merges of the same stack, because the quantity of interest is the aura's
depth relative to that image's own backdrop -- which is what the eye sees. It
was NOT legitimate for comparing a merge to single frames carrying a 3530 DN
exposure spread, which is the error that produced the false "the merge is worse
than every one of its inputs" reading.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, binary_closing, binary_opening

SRC = Path(r"C:\dev\strehl-out\ORCH-rim")
OUT = Path(r"C:\dev\strehl-out\AURA")
ARMS = {"photometric OFF (shipped)": OUT / "fba-merge.tif",
        "photometric ON": OUT / "fba-merge-photo.tif"}
ELECT = {"photometric OFF (shipped)": OUT / "fba-election.tif",
         "photometric ON": OUT / "fba-photo-election.tif"}

BANDS = [(1, 16), (16, 32), (32, 64), (64, 96), (96, 140), (140, 200),
         (200, 260), (260, 320), (320, 400), (400, 500)]
FAR = (500, 900)


def luma(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    out = (0.2126 * a[..., 0].astype(np.float32)
           + 0.7152 * a[..., 1].astype(np.float32)
           + 0.0722 * a[..., 2].astype(np.float32)) if a.ndim == 3 \
        else a.astype(np.float32)
    del a
    return out


def main() -> int:
    f = luma(SRC / "frame102-lin.tif")
    b = float(np.median(f))
    subj = f < 0.5 * b
    del f
    subj = binary_closing(subj, np.ones((9, 9)))
    subj = binary_opening(subj, np.ones((9, 9)))
    dist = distance_transform_edt(~subj)
    # The merges are 3520x2344; the mask is built at 7040x4688 from a single
    # frame and subsampled, so both refer to the same physical boundary.
    subj_e = subj[::2, ::2]
    dist_e = dist[::2, ::2]
    del subj, dist

    masks, counts = [], []
    for lo, hi in BANDS:
        m = (dist_e >= lo) & (dist_e < hi) & ~subj_e
        masks.append(m)
        counts.append(int(m.sum()))
    far_m = (dist_e >= FAR[0]) & (dist_e < FAR[1]) & ~subj_e

    profs = {}
    for name, path in ARMS.items():
        if not path.exists():
            print(f"  MISSING {path}")
            return 2
        img = luma(path)
        if img.shape != subj_e.shape:
            print(f"  FATAL: {name} is {img.shape}, mask is {subj_e.shape}")
            return 2
        ref = float(np.median(img[far_m]))
        profs[name] = (np.array([float(np.median(img[m])) - ref for m in masks]),
                       ref)
        del img

    names = list(ARMS)
    a, b_ = profs[names[0]][0], profs[names[1]][0]
    print(f"  far-field level: {names[0]} {profs[names[0]][1]:.1f} DN, "
          f"{names[1]} {profs[names[1]][1]:.1f} DN")
    print()
    print("  band(px)       n px     OFF (DN)      ON (DN)     change   "
          "% of aura removed")
    print("  " + "-" * 78)
    for i, (lo, hi) in enumerate(BANDS):
        rem = 100.0 * (1.0 - abs(b_[i]) / abs(a[i])) if a[i] else float("nan")
        print(f"  {lo:4d}-{hi:4d} {counts[i]:10,} {a[i]:12.1f} {b_[i]:12.1f} "
              f"{b_[i]-a[i]:10.1f} {rem:17.1f}%")

    aura = [i for i, (lo, hi) in enumerate(BANDS) if 64 <= lo < 260]
    off_a = float(np.mean([a[i] for i in aura]))
    on_a = float(np.mean([b_[i] for i in aura]))
    print()
    print(f"  aura band d=64-260 px")
    print(f"    photometric OFF (shipped) : {off_a:9.1f} DN")
    print(f"    photometric ON            : {on_a:9.1f} DN")
    print(f"    removed                   : {100*(1-abs(on_a)/abs(off_a)):8.1f}%")

    # The rim, which is a different feature and must be reported separately so
    # a win on one is not read as a win on both.
    print(f"\n  rim band d=1-32 px (feature 1, section 22.1 -- a DIFFERENT defect)")
    print(f"    OFF {np.mean(a[:2]):9.1f} DN     ON {np.mean(b_[:2]):9.1f} DN")

    # ---- did the election ramp itself change? ----------------------------
    print()
    print("  median elected frame by band (the ramp from section 22.4):")
    print("  band(px)        OFF     ON")
    for name in names:
        pass
    els = {}
    for name, p in ELECT.items():
        if not p.exists():
            continue
        e = tifffile.imread(str(p))
        if e.ndim == 3:
            e = e[..., 0]
        els[name] = e.astype(np.int32)
    if len(els) == 2:
        for i, (lo, hi) in enumerate(BANDS):
            if counts[i] < 2000:
                continue
            v0 = float(np.median(els[names[0]][masks[i]]))
            v1 = float(np.median(els[names[1]][masks[i]]))
            print(f"  {lo:4d}-{hi:4d} {v0:10.1f} {v1:6.1f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
