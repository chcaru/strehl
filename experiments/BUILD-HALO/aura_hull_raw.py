"""Is the merge really outside the hull of its inputs? Test it in raw DN.

`aura_hull.py` found the merge darker than all nine sampled frames at 77% of
pixels, using each arm's own far-field median as its reference. That test has
an assumption in it that must be checked before the result can be believed.

The convexity identity is

    merge(p) = sum_k w_k(p) * frame_k(p)      =>   min_k <= merge <= max_k

which is exact in RAW DN at a single pixel. Referencing each arm to its own far
field preserves it ONLY IF every frame carries the same physical value V in the
far field, because the merge's own reference is then sum_k w_k(far)*V = V
regardless of the weights, which differ from pixel to pixel. If instead the arms
carry different global render offsets or gains, the reference subtracts a
different quantity from each arm and the hull test is measuring those offsets
rather than the merge.

So this measures the raw far-field level of every arm directly. If they agree
tightly, both objections vanish and the referenced test stands as run. If they
do not, the raw test below is the one to believe, because it needs no reference
at all -- at the cost of being confounded by any real global offset, which is
then reported rather than assumed away.

Both are printed. Where they disagree, the raw test wins on validity and the
disagreement itself is the finding.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, binary_closing, binary_opening

SRC = Path(r"C:\dev\strehl-out\ORCH-rim")
FRAMES = {0: "f0-lin.tif", 25: "fb-f025-lin.tif", 51: "fb-f051-lin.tif",
          76: "fb-f076-lin.tif", 102: "frame102-lin.tif", 127: "fb-f127-lin.tif",
          153: "fb-f153-lin.tif", 178: "fb-f178-lin.tif", 204: "f204-lin.tif"}
MERGE = "merge-lin.tif"
TARGET = (140, 200)
FAR = (500, 900)
NSAMPLE = 40000
RNG = np.random.default_rng(20260825)


def luma(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    out = (0.2126 * a[..., 0].astype(np.float32)
           + 0.7152 * a[..., 1].astype(np.float32)
           + 0.0722 * a[..., 2].astype(np.float32)) if a.ndim == 3 \
        else a.astype(np.float32)
    del a
    return out


def main() -> int:
    f = luma(SRC / FRAMES[102])
    b = float(np.median(f))
    subj = f < 0.5 * b
    del f
    subj = binary_closing(subj, np.ones((9, 9)))
    subj = binary_opening(subj, np.ones((9, 9)))
    d = distance_transform_edt(~subj)
    tgt = (d >= TARGET[0]) & (d < TARGET[1]) & ~subj
    far = (d >= FAR[0]) & (d < FAR[1]) & ~subj
    del d, subj

    idx = np.flatnonzero(tgt.ravel())
    pick = RNG.choice(idx, size=NSAMPLE, replace=False)
    # A frozen far-field pixel sample too, so every arm's far level is read at
    # exactly the same pixels -- otherwise a median over slightly different
    # populations contributes its own difference.
    fidx = np.flatnonzero(far.ravel())
    fpick = RNG.choice(fidx, size=NSAMPLE, replace=False)
    del tgt, far

    keys = sorted(FRAMES)
    raw = np.zeros((len(keys), NSAMPLE), dtype=np.float32)
    farlvl = {}
    print("  arm        far-field raw DN      target raw DN")
    print("  " + "-" * 50)
    for j, k in enumerate(keys):
        img = luma(SRC / FRAMES[k]).ravel()
        raw[j] = img[pick]
        farlvl[k] = float(np.median(img[fpick]))
        del img
        print(f"  f{k:03d}      {farlvl[k]:14.1f}   {np.median(raw[j]):14.1f}")

    img = luma(SRC / MERGE).ravel()
    mraw = img[pick]
    mfar = float(np.median(img[fpick]))
    del img
    print(f"  MERGE     {mfar:14.1f}   {np.median(mraw):14.1f}")

    lv = np.array(list(farlvl.values()))
    spread = float(lv.max() - lv.min())
    print(f"\n  far-field spread ACROSS the 9 frames : {spread:8.1f} DN")
    print(f"  merge far field minus frame mean      : "
          f"{mfar - float(lv.mean()):8.1f} DN")
    print(f"  (both must be small against the ~4000 DN aura for the")
    print(f"   referenced hull test in aura_hull.py to have been valid)")

    # ---- the raw hull test, which needs no reference ----------------------
    fmin = raw.min(axis=0)
    below = float((mraw < fmin).mean())
    depth = float(np.median((fmin - mraw)[mraw < fmin])) if below else 0.0
    print()
    print(f"  RAW hull test (no reference anywhere):")
    print(f"    merge below every sampled frame : {100*below:6.2f}% of pixels")
    print(f"    median depth below the hull     : {depth:8.1f} DN")

    # ---- and the same test with the far reference, for comparison --------
    exc = raw - np.array([farlvl[k] for k in keys], dtype=np.float32)[:, None]
    mexc = mraw - mfar
    below_r = float((mexc < exc.min(axis=0)).mean())
    print(f"  REFERENCED hull test (as aura_hull.py ran it):")
    print(f"    merge below every sampled frame : {100*below_r:6.2f}% of pixels")

    print()
    if spread < 200 and abs(mfar - float(lv.mean())) < 200:
        print("  => the arms agree in the far field, so BOTH tests are valid")
        print("     and they should agree. They do." if abs(below - below_r)
              < 0.05 else "     but they DISAGREE, which needs explaining.")
    else:
        print("  => the arms do NOT agree in the far field. The referenced")
        print("     test was measuring those offsets in part. Believe the RAW")
        print("     number above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
