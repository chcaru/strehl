"""M116 addendum -- hunt for motion-won pixels in the election map.

ORCH's correction (19:24, post-registration) cites corpus fact 1189 / M89: a
frame that MOVED between exposures presents a displaced edge, a displaced edge
is sharper than the correctly-focused stationary alternative, so motion does not
merely survive the per-pixel election -- it WINS it. M89 measured 4.78% of
foam's output pixels taking their value from a frame >8 sigma discrepant.

Detector. In a clean focus sweep the elected frame index varies SMOOTHLY across
the scene, because focus does. Two things break that smoothness and they are
not the same thing:

  a depth discontinuity  -> a LARGE, COHERENT region elects a distant frame.
                            Legitimate. An occluding edge must produce this.
  a motion-won pixel     -> a SMALL, ISOLATED speckle elects a distant frame
                            while all its neighbours elect a nearby one.

So the statistic is not "index residual is large" -- that would convict every
occluding edge in the library. It is "index residual is large AND the connected
component carrying it is small". tweezers-cpl is the built-in trap: it is a
rigid steel tool with a hard occluding edge, so it must show large coherent
index structure and few isolated speckles. A detector that ranks tweezers top
is measuring depth, not motion, and is refuted.

STATED FAILURE DIRECTION (AGENTS.md rule 18): this fires on anything that makes
one pixel elect a distant frame in isolation -- a hot pixel, a cosmic ray, or
fine structure at the resolution limit would all qualify. It is a proxy for
motion, not a measurement of it. The images are the evidence; this only says
where to look.
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

ROOT = Path(r"C:\dev\strehl-out\M116")
MAPS = ROOT / "maps"
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]

MED = 9          # neighbourhood the election is compared against
JUMP = 8         # frames of index discrepancy to count as "distant"
MAX_BLOB = 64    # plane px; larger than this is a depth feature, not a speckle
TOP = 6          # clusters to crop per subject


def main() -> int:
    out = {}
    for s in SUBJECTS:
        p = MAPS / f"{s}__A0-index.tif"
        if not p.exists():
            print(f"{s}: no index map")
            continue
        idx = tifffile.imread(p).astype(np.float32)
        if idx.ndim == 3:
            idx = idx[..., 0]

        smooth = ndimage.median_filter(idx, size=MED)
        resid = np.abs(idx - smooth)
        far = resid >= JUMP

        lab, n = ndimage.label(far)
        if n == 0:
            print(f"{s}: no discrepant pixels at all")
            continue
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0

        small_lut = np.zeros(sizes.size, dtype=bool)
        keep = np.flatnonzero((sizes > 0) & (sizes <= MAX_BLOB))
        small_lut[keep] = True
        small = small_lut[lab]          # O(n) lookup, not O(n x clusters)
        big = far & ~small

        tot = idx.size
        pct_far = 100.0 * far.sum() / tot
        pct_iso = 100.0 * small.sum() / tot
        pct_coh = 100.0 * big.sum() / tot

        # rank isolated clusters by how far they jumped. Vectorised over labels:
        # a `lab == lb` scan per cluster is O(clusters x 8M) and does not
        # finish on a real map.
        cl = []
        if keep.size:
            kl = [int(v) for v in keep]
            coms = ndimage.center_of_mass(far, lab, kl)
            jumps = ndimage.maximum(resid, lab, kl)
            if keep.size == 1:
                coms, jumps = [coms], [jumps]
            for lb, (cy, cx), j in zip(kl, coms, jumps):
                cl.append({"y": int(cy), "x": int(cx),
                           "px": int(sizes[lb]), "jump": float(j)})
        cl.sort(key=lambda c: (-c["jump"], -c["px"]))

        print(f"\n== {s} ==")
        print(f"  elected index range      : {idx.min():.0f}..{idx.max():.0f}")
        print(f"  discrepant (>= {JUMP} frames): {pct_far:.3f}% of output pixels")
        print(f"    of which ISOLATED       : {pct_iso:.3f}%  <- motion candidates")
        print(f"    of which COHERENT       : {pct_coh:.3f}%  <- depth structure")
        print(f"  isolated clusters         : {len(cl)}")
        for c in cl[:TOP]:
            print(f"      ({c['x']:5d},{c['y']:5d})  {c['px']:3d} px  "
                  f"jump {c['jump']:.0f} frames")

        out[s] = {
            "pct_discrepant": pct_far, "pct_isolated": pct_iso,
            "pct_coherent": pct_coh, "n_isolated_clusters": len(cl),
            "clusters": cl[:TOP],
        }

    (ROOT / "motion-hunt.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {ROOT / 'motion-hunt.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
