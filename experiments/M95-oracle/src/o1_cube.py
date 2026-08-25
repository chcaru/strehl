"""O1 -- build the through-focus cube: every frame, every ROI, G1 and G2 separately.

WHY G1 AND G2 SEPARATELY. This is the whole instrument. The election is an
argmax over 299 noisy per-frame scores, so it suffers a winner's curse: it
maximises signal+noise, not signal. Any oracle that is ALSO an argmax over the
same data suffers its own curse, and comparing them would measure the difference
of two curses rather than the election's error.

An RGGB quad carries TWO green photosites, G1 at (0,1) and G2 at (1,0). They see
the same scene through the same optics at the same instant, with INDEPENDENT
read and shot noise. So: SELECT the frame using G1, EVALUATE the detail using G2.
The evaluation data is then independent of the selection data and the curse
cancels for whichever rule did the selecting -- elector and oracle alike, on
exactly equal terms.

No strehl render is needed for the cube. The binned-linear output averages
(G1+G2)/2 and would destroy the split, so the cube is decoded straight from the
ARW. The rendered TIFFs are still used, separately, to recover the REAL election
map by byte-identity, which is what validates that the modelled elector is
faithful to the shipped one.

Reads D:\personal\macro\bee-3-cpl read-only. Writes only under C:\dev\strehl-out.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "M95-merge-vs-frame", "src"))
import m95lib as L  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

CUBE = r"C:\dev\strehl-out\M95-oracle"
WIN = 512
MARGIN = 32
SIDE = WIN + 2 * MARGIN

ROIS = {
    "ROI-LOWDRIFT": (576, 64),
    "ROI-MIDDRIFT": (2112, 64),
    "ROI-HIGHDRIFT": (2368, 320),
    "ROI-FLAT": (2112, 1088),
}


def main() -> int:
    os.makedirs(CUBE, exist_ok=True)
    paths = sorted(
        os.path.join(L.STACK, f) for f in os.listdir(L.STACK) if f.lower().endswith(".arw")
    )
    n = len(paths)
    print(f"frames: {n}")
    print(f"cube  : {CUBE}")
    print(f"ROIs  : {list(ROIS)}  win={WIN} margin={MARGIN} side={SIDE}")

    mm = {}
    for nm in ROIS:
        for g in ("g1", "g2"):
            p = os.path.join(CUBE, f"{nm}.{g}.npy")
            mm[(nm, g)] = np.lib.format.open_memmap(
                p, mode="w+", dtype=np.uint16, shape=(n, SIDE, SIDE)
            )

    meta = {"n": n, "win": WIN, "margin": MARGIN, "side": SIDE, "rois": ROIS,
            "arw": [os.path.basename(p) for p in paths], "levels": []}

    t0 = time.time()
    for i, p in enumerate(paths):
        r = L.decode_raw(p)
        g1 = r.cfa[0::2, 1::2]
        g2 = r.cfa[1::2, 0::2]
        if i == 0:
            meta["black"] = r.black
            meta["white"] = r.white
            meta["pattern"] = r.pattern
            meta["plane_shape"] = list(g1.shape)
            print(f"black={r.black} white={r.white} pattern={r.pattern} plane={g1.shape}")
        lv = {}
        for nm, (x, y) in ROIS.items():
            y0, x0 = y - MARGIN, x - MARGIN
            assert y0 >= 0 and x0 >= 0, (nm, y0, x0)
            assert y0 + SIDE <= g1.shape[0] and x0 + SIDE <= g1.shape[1], (nm, g1.shape)
            a = g1[y0:y0 + SIDE, x0:x0 + SIDE]
            b = g2[y0:y0 + SIDE, x0:x0 + SIDE]
            mm[(nm, "g1")][i] = a
            mm[(nm, "g2")][i] = b
            lv[nm] = [float(a.mean()), float(b.mean())]
        meta["levels"].append(lv)
        if i % 25 == 0 or i == n - 1:
            el = time.time() - t0
            print(f"  [{i+1:3d}/{n}] {el:6.1f}s  eta {el/(i+1)*(n-i-1):6.1f}s", flush=True)

    for k, v in mm.items():
        v.flush()
    with open(os.path.join(CUBE, "cube_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    print(f"\ndone in {time.time()-t0:.1f}s")

    # Distinctness: two frames that decoded to identical bytes would make any
    # through-focus curve flat for a reason that has nothing to do with focus.
    a = mm[("ROI-LOWDRIFT", "g1")]
    h = [hash(a[i].tobytes()) for i in range(n)]
    print(f"distinctness: {n} frames, {len(set(h))} unique ROI-LOWDRIFT.g1 crops")
    assert len(set(h)) == n, "duplicate frames in the cube"

    # G1 and G2 must NOT be identical -- if they were, the cross-fit would be a
    # sham and every 'independent' evaluation would reuse the selection noise.
    b = mm[("ROI-LOWDRIFT", "g2")]
    same = int(np.count_nonzero(a[183] == b[183]))
    tot = SIDE * SIDE
    print(f"G1 vs G2 on frame 183: {same}/{tot} equal ({100.0*same/tot:.3f} %)")
    assert same < tot // 2, "G1 and G2 are not independent samples"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
