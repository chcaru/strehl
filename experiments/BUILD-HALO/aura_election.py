"""Which frames does the backdrop elect, and are they the veiled ones?

The reconstruction in `aura_reconstruct.py` showed the merge's backdrop at
d=117 px sitting at -5063 DN, between frame 0 (-6194) and frame 25 (-4836),
while a uniform mean of nine frames gives only -2136. That is an INFERENCE that
the election prefers the most-defocused frames. This measures it directly.

The mechanism under test:

    A backdrop pixel 100 px from the subject is featureless. The only structure
    present in ANY frame is the subject's own defocus skirt reaching that far.
    A skirt is a smooth ramp, a ramp carries gradient energy, and the ramp is
    steepest in the frames where the subject is MOST defocused and spilling
    furthest. The focus measure is a gradient statistic, so it is maximised by
    the frame carrying the most veil. The election therefore SEEKS the
    contaminated frames rather than merely tolerating them.

Predictions, which differ from every rival:

  * near the subject (d ~ 30-260 px) the elected index concentrates at ONE END
    of the bracket -- the most-defocused end -- and NOT at the subject's own
    focus (~frame 153), and NOT uniformly.
  * far from the subject (d > 500 px) no frame's skirt reaches, so there is no
    veil gradient to elect, the election reverts to dead-ground noise, and the
    distribution goes broad. This is BUILD-HALO section 21's result and it is
    the built-in control: the same plane, the same statistic, a region where
    the mechanism predicts its own absence.
  * the transition between the two happens near the subject's maximum blur
    radius, which is where the aura was measured to terminate (~320 px).

Grid: the election map is 3520x2344 and ORCH's TIFFs are 7040x4688, so the map
is at HALF the linear scale. The silhouette is built at full resolution from
frame 102 (a single frame, no election in it -- the same independence
discipline as section 21) and then subsampled, rather than being rebuilt at low
resolution, so both analyses refer to the same physical boundary. Distances are
reported in TIFF px throughout, converting the map's own px by 2.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, binary_closing, binary_opening

SRC = Path(r"C:\dev\strehl-out\ORCH-rim")
OUT = Path(r"C:\dev\strehl-out\AURA")
ELECTION = OUT / "fba-election.tif"
F102 = SRC / "frame102-lin.tif"

# Bands in TIFF px, matching aura_reconstruct.py so the two tables align.
BANDS = [(1, 8), (8, 16), (16, 32), (32, 64), (64, 96), (96, 140),
         (140, 200), (200, 260), (260, 320), (320, 400), (400, 500),
         (500, 700), (700, 1000), (1000, 1600)]
NFRAMES = 205
SUBJECT_FOCUS = 153  # measured in aura_reconstruct: shallowest d=6 spill


def main() -> int:
    el = tifffile.imread(str(ELECTION))
    if el.ndim == 3:
        el = el[..., 0]
    el = el.astype(np.int32)
    print(f"election map {el.shape}  range {el.min()}..{el.max()}")

    a = tifffile.imread(str(F102))
    f = (0.2126 * a[..., 0].astype(np.float32)
         + 0.7152 * a[..., 1].astype(np.float32)
         + 0.0722 * a[..., 2].astype(np.float32))
    del a
    backdrop = float(np.median(f))
    subject = f < 0.5 * backdrop
    del f
    subject = binary_closing(subject, np.ones((9, 9)))
    subject = binary_opening(subject, np.ones((9, 9)))
    print(f"silhouette built at {subject.shape}, covers {100*subject.mean():.2f}%")

    dist = distance_transform_edt(~subject)  # TIFF px, 0 inside the subject

    # Subsample onto the election grid. Verified, not assumed.
    sy = subject.shape[0] // el.shape[0]
    sx = subject.shape[1] // el.shape[1]
    if (sy, sx) != (2, 2):
        print(f"  FATAL: expected a 2x2 grid ratio, measured {(sy, sx)}")
        return 2
    subj_e = subject[::2, ::2][: el.shape[0], : el.shape[1]]
    dist_e = dist[::2, ::2][: el.shape[0], : el.shape[1]]
    del subject, dist
    print(f"  grid ratio {sy}x{sx} confirmed; distances reported in TIFF px")

    print()
    print("  band(TIFF px)      n px   median  p10  p90    IQR   frac<=40  "
          "frac>=140   spread")
    print("  " + "-" * 86)
    rows = []
    for lo, hi in BANDS:
        m = (dist_e >= lo / 2) & (dist_e < hi / 2) & ~subj_e
        n = int(m.sum())
        if n < 2000:
            continue
        v = el[m]
        med = float(np.median(v))
        p10, p90 = np.percentile(v, [10, 90])
        q1, q3 = np.percentile(v, [25, 75])
        # "spread" is the IQR as a fraction of the whole bracket: near 0 means
        # the band agrees on one frame, near 1 means it is electing noise.
        spread = (q3 - q1) / NFRAMES
        lowend = float((v <= 40).mean())
        highend = float((v >= 140).mean())
        rows.append((lo, hi, n, med, spread, lowend, highend))
        print(f"  {lo:5d}-{hi:5d} {n:10,} {med:8.1f} {p10:5.0f} {p90:5.0f} "
              f"{q3-q1:6.0f} {lowend:9.3f} {highend:10.3f} {spread:8.3f}")

    # ---- the verdict ------------------------------------------------------
    near = [r for r in rows if 32 <= r[0] < 260]
    far = [r for r in rows if r[0] >= 500]
    if not near or not far:
        print("  FATAL: a comparison band is empty")
        return 2
    near_med = float(np.mean([r[3] for r in near]))
    far_med = float(np.mean([r[3] for r in far]))
    near_spread = float(np.mean([r[4] for r in near]))
    far_spread = float(np.mean([r[4] for r in far]))
    near_low = float(np.mean([r[5] for r in near]))
    far_low = float(np.mean([r[5] for r in far]))

    print()
    print(f"  aura band d=32-260 px : median frame {near_med:6.1f}   "
          f"IQR/bracket {near_spread:.3f}   frac electing <=40: {near_low:.3f}")
    print(f"  far  band d>=500  px : median frame {far_med:6.1f}   "
          f"IQR/bracket {far_spread:.3f}   frac electing <=40: {far_low:.3f}")
    print(f"  the subject's OWN focus is frame {SUBJECT_FOCUS}")
    print()
    if near_med < 60 and near_spread < far_spread:
        print("  => the aura band elects the MOST-DEFOCUSED end of the bracket,")
        print("     and does so more decisively than the far field elects "
              "anything.")
        print("     The election is not tolerating the veil, it is SEEKING it.")
    else:
        print("  => the prediction FAILED; the aura band does not concentrate "
              "at the defocused end.")

    # ---- the picture ------------------------------------------------------
    try:
        from PIL import Image
        s = 3
        e = el[::s, ::s].astype(np.float32)
        d = dist_e[::s, ::s]
        sj = subj_e[::s, ::s]
        # Index 0 (most defocused) -> red, index 204 -> blue.
        t = np.clip(e / NFRAMES, 0, 1)
        rgb = np.dstack([
            ((1 - t) * 255).astype(np.uint8),
            (np.minimum(t, 1 - t) * 2 * 120).astype(np.uint8),
            (t * 255).astype(np.uint8),
        ])
        rgb[sj] = [40, 40, 40]
        ring = ((d >= 16) & (d < 130) & ~sj)
        edge = ring ^ binary_opening(ring, np.ones((3, 3)))
        rgb[edge] = [255, 255, 255]
        p = OUT / "AURA-election.png"
        Image.fromarray(rgb).save(p)
        assert p.read_bytes()[:4] == b"\x89PNG"
        print(f"\n  wrote {p}")
        print("  RED = elects the defocused end (frame 0).  "
              "BLUE = elects frame 204.")
        print("  white ring bounds the aura band; grey is the subject.")
    except Exception as exc:  # noqa: BLE001
        print(f"  overlay failed: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
