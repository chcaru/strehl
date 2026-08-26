"""Can the dark aura be rebuilt from single frames alone?

ORCH measured a broad dark aura on `flower-bud-alone-cpl`, peaking at -4293 DN
at d=117 px from the silhouette -- 22.8% of the backdrop -- and proposed that
backdrop pixels are OCCLUDED by the subject in many frames because focus
breathing moves the silhouette, so occluded samples are averaged in.

This tests a rival driver that needs no silhouette motion whatsoever:

    The backdrop is featureless. A featureless field has no focus signal, so
    the election is dead ground (BUILD-HALO section 21) and the noise gate finds
    every frame statistically tied and admits ~55 of them, scattered across the
    bracket. In most of those frames the SUBJECT is heavily defocused and its
    dark skirt spans hundreds of px. Averaging them pulls the backdrop dark.

The two are separable by a reconstruction, and the separation is clean:

  * every single-frame arm here is a `STREHL_ONLY_FRAME` render, which re-solves
    alignment with that frame as its own reference, so each is IDENTITY-warped.
  * therefore a profile built by averaging those frames contains NO inter-frame
    registration, and hence no breathing and no occlusion-by-motion, BY
    CONSTRUCTION. Breathing cannot contribute to it even in principle.

So if the mean of the single frames reproduces the merge's dark aura, the aura
is defocus spill through the average and breathing is not the driver. If the
mean instead looks like the subject-focused frame -- no aura -- then averaging
is exonerated and the defect is elsewhere in the merge.

This is a PREDICTIVE test, not a descriptive one: the reconstruction is built
from arms that were rendered for another purpose and never tuned to match.

Memory: the TIFFs are ~198 MB each and the tree is shared with four other
agents' renders. Frames are loaded ONE AT A TIME, reduced to a profile, and
dropped; peak residency is one frame plus the masks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, binary_closing, binary_opening

SRC = Path(r"C:\dev\strehl-out\ORCH-rim")
OUT = Path(r"C:\dev\strehl-out\AURA")

# Nine evenly spaced frames across the 205-frame bracket, as rendered by ORCH.
FRAMES = {
    0: "f0-lin.tif",
    25: "fb-f025-lin.tif",
    51: "fb-f051-lin.tif",
    76: "fb-f076-lin.tif",
    102: "frame102-lin.tif",
    127: "fb-f127-lin.tif",
    153: "fb-f153-lin.tif",
    178: "fb-f178-lin.tif",
    204: "f204-lin.tif",
}
MERGE = "merge-lin.tif"

# Bands are edges in px outward from the silhouette.
BANDS = [(1, 4), (4, 8), (8, 12), (12, 16), (16, 24), (24, 32), (32, 48),
         (48, 64), (64, 96), (96, 140), (140, 200), (200, 260), (260, 320),
         (320, 400)]
# The far-field reference. ORCH used 300-400, but he also measured the aura
# terminating near d=320, so that band is partly inside the feature it is
# meant to reference. Using it would bias the result TOWARD zero -- i.e. it
# understates the aura -- so it is not the source of his effect, but it is
# still the wrong band. Referenced further out, and reported both ways.
FAR = (500, 900)
FAR_ORCH = (300, 400)


def luma(path: Path) -> np.ndarray:
    """Linear luma as float32. Drops the uint16 immediately -- these are 198 MB."""
    a = tifffile.imread(str(path))
    if a.ndim == 3:
        out = (0.2126 * a[..., 0].astype(np.float32)
               + 0.7152 * a[..., 1].astype(np.float32)
               + 0.0722 * a[..., 2].astype(np.float32))
    else:
        out = a.astype(np.float32)
    del a
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- the silhouette, from the subject-focused frame -------------------
    # Frame 102 is the bracket's middle and its subject is the sharpest
    # available, so its silhouette is the least blur-dilated of any frame. It
    # is a single frame with no election in it, so the mask is independent of
    # the merge under test -- the same independence discipline as section 21.
    print("loading frame 102 for the silhouette ...", flush=True)
    f102 = luma(SRC / FRAMES[102])
    backdrop = float(np.median(f102))
    # A dark subject on a bright backdrop: the histogram is strongly bimodal
    # and the threshold sits in the empty valley, so its exact placement is
    # not load-bearing. Verified by the mask overlay this script writes.
    thr = 0.5 * backdrop
    subject = f102 < thr
    subject = binary_closing(subject, np.ones((9, 9)))
    subject = binary_opening(subject, np.ones((9, 9)))
    print(f"  backdrop median {backdrop:9.1f} DN   threshold {thr:9.1f} DN")
    print(f"  subject covers {100.0 * subject.mean():.2f}% of frame")

    # distance_transform_edt returns 0 INSIDE the mask, so distance is measured
    # on the complement and the subject itself is excluded from every band.
    print("distance transform ...", flush=True)
    dist = distance_transform_edt(~subject)
    del f102

    # Freeze the band masks once, so every arm is measured on identical pixel
    # sets and no arm can move its own goalposts.
    band_masks = [((dist >= lo) & (dist < hi) & ~subject) for lo, hi in BANDS]
    far_mask = (dist >= FAR[0]) & (dist < FAR[1]) & ~subject
    far_orch = (dist >= FAR_ORCH[0]) & (dist < FAR_ORCH[1]) & ~subject
    counts = [int(m.sum()) for m in band_masks]
    print(f"  far field {FAR} has {int(far_mask.sum()):,} px")
    if far_mask.sum() < 10000:
        print("  FATAL: far-field reference is too small to be a reference")
        return 2

    # ---- a subject-free control, to prove the instrument is quiet ---------
    # Everything at d > FAR[1] with no silhouette anywhere near it. If the
    # pipeline reports a large deviation HERE, the profile means nothing.
    ctrl = dist >= 1200
    print(f"  control (d>=1200) {int(ctrl.sum()):,} px")

    def profile(img: np.ndarray) -> tuple[np.ndarray, float, float]:
        far = float(np.median(img[far_mask]))
        vals = np.array([float(np.median(img[m])) - far if counts[i] else np.nan
                         for i, m in enumerate(band_masks)])
        ctrl_dev = float(np.median(img[ctrl])) - far if ctrl.sum() else np.nan
        orch_far = float(np.median(img[far_orch])) - far
        return vals, ctrl_dev, orch_far

    # ---- every arm, one at a time ----------------------------------------
    profs: dict[str, np.ndarray] = {}
    ctrls: dict[str, float] = {}
    stack = np.zeros((len(FRAMES), len(BANDS)), dtype=np.float64)

    for j, (k, name) in enumerate(sorted(FRAMES.items())):
        p = SRC / name
        if not p.exists():
            print(f"  MISSING {name}")
            return 2
        img = luma(p)
        vals, cd, orch_far = profile(img)
        del img
        profs[f"f{k:03d}"] = vals
        ctrls[f"f{k:03d}"] = cd
        stack[j] = vals
        print(f"  frame {k:3d}: d=6 {vals[1]:9.1f}   d=117 {vals[9]:9.1f}   "
              f"ctrl {cd:7.1f}   orch-far {orch_far:7.1f}", flush=True)

    img = luma(SRC / MERGE)
    merge_p, merge_ctrl, merge_orch_far = profile(img)
    del img
    print(f"  MERGE    : d=6 {merge_p[1]:9.1f}   d=117 {merge_p[9]:9.1f}   "
          f"ctrl {merge_ctrl:7.1f}   orch-far {merge_orch_far:7.1f}")

    recon = stack.mean(axis=0)

    # ---- the table --------------------------------------------------------
    print()
    print("  band(px)     n px      merge   f102(sharp)   MEAN-OF-9     "
          "merge-f102   merge-recon")
    print("  " + "-" * 88)
    for i, (lo, hi) in enumerate(BANDS):
        print(f"  {lo:4d}-{hi:4d} {counts[i]:10,} {merge_p[i]:10.1f} "
              f"{profs['f102'][i]:12.1f} {recon[i]:12.1f} "
              f"{merge_p[i] - profs['f102'][i]:13.1f} "
              f"{merge_p[i] - recon[i]:13.1f}")

    # ---- the verdict ------------------------------------------------------
    # The aura band is where ORCH measured the peak. "Explained" means the
    # reconstruction closes the gap between the sharp frame and the merge.
    aura = [i for i, (lo, hi) in enumerate(BANDS) if 64 <= lo < 260]
    gap = float(np.mean([merge_p[i] - profs["f102"][i] for i in aura]))
    resid = float(np.mean([merge_p[i] - recon[i] for i in aura]))
    explained = 100.0 * (1.0 - abs(resid) / abs(gap)) if gap else float("nan")

    print()
    print(f"  aura band d=64-260 px")
    print(f"    merge - sharp frame      : {gap:9.1f} DN   <- the defect")
    print(f"    merge - mean of 9 frames : {resid:9.1f} DN   <- what averaging "
          f"does NOT explain")
    print(f"    explained by averaging   : {explained:8.1f}%")
    print()
    print(f"  control deviations (must be small vs {abs(gap):.0f} DN):")
    print(f"    merge {merge_ctrl:7.1f}    f102 {ctrls['f102']:7.1f}    "
          f"f000 {ctrls['f000']:7.1f}    f204 {ctrls['f204']:7.1f}")

    np.savez(OUT / "aura_reconstruct.npz", bands=np.array(BANDS),
             counts=np.array(counts), merge=merge_p, recon=recon,
             stack=stack, keys=np.array(sorted(FRAMES)))

    # The mask overlay. Section 19.6: the picture outranks the scalar, and two
    # segmentation failures on this project were caught only by drawing one.
    try:
        from PIL import Image
        f = luma(SRC / FRAMES[102])
        s = 6
        small = f[::s, ::s]
        del f
        v = np.clip(small / max(backdrop, 1.0) * 200.0, 0, 255).astype(np.uint8)
        rgb = np.dstack([v, v, v])
        ss = subject[::s, ::s]
        edge = ss ^ binary_opening(ss, np.ones((3, 3)))
        rgb[edge] = [0, 255, 0]
        ds = dist[::s, ::s]
        for lo, hi in [(64, 260)]:
            ring = (ds >= lo) & (ds < hi) & ~ss
            r = ring ^ binary_opening(ring, np.ones((3, 3)))
            rgb[r] = [255, 0, 0]
        p = OUT / "AURA-mask.png"
        Image.fromarray(rgb).save(p)
        assert p.read_bytes()[:4] == b"\x89PNG"
        print(f"\n  wrote {p}  (green=silhouette, red=aura band 64-260px)")
    except Exception as e:  # noqa: BLE001
        print(f"  overlay failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
