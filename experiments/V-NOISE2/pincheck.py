"""pincheck -- does the binary change the measured pixels?

SEC.11.4 CONTROL.  bee's original arms were built with pin 740e7056; ORCH
requires 9b05d0b7 (sha16 44C2F2CD2E5B2894) for the M115 ladder.  Mixing them
across rungs would confound binary with N, so every rung was rebuilt on
9b05d0b7.  bee-L4 is stride 1 with the same parity split as the original bee
build, so `bee/arms/strehl-A.tiff` and `bee-L4/arms/strehl-A.tiff` are THE SAME
COMPUTATION UNDER TWO BINARIES -- a controlled comparison that costs nothing
because both files already exist.

ORCH: "Compare decoded arrays, never file hashes -- I overturned a correct
finding tonight on TIFFs that differed only in an ImageDescription tag."  So
this decodes both and compares pixels.  A file-hash comparison is ALSO printed,
purely to show whether the two would have disagreed, because that is the whole
point of the warning.

WHAT THE ANSWER LICENSES.  If the decoded arrays are identical, sec.9's `119`
reading (built on 740e7056) and this ladder are on one binary for all
measurement purposes and may be discussed together.  If they differ, they may
not, and the ladder stands alone.

    python pincheck.py
"""
import hashlib
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import incoh as I                                                # noqa: E402
import hd2                                                       # noqa: E402

Comp = I.Comp

PAIRS = (("strehl-A.tiff", "740e7056", "9b05d0b7"),
         ("strehl-B.tiff", "740e7056", "9b05d0b7"))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16].upper()


def main():
    print("=" * 100)
    print("PINCHECK -- 740e7056 (bee) vs 9b05d0b7 (bee-L4), same frames, same split")
    print("=" * 100)
    worst = 0.0
    for fn, pa, pb in PAIRS:
        a = os.path.join(hd2.ROOT, "bee", "arms", fn)
        b = os.path.join(hd2.ROOT, "bee-L4", "arms", fn)
        if not (os.path.exists(a) and os.path.exists(b)):
            print(f"  {fn}: MISSING one side -- skipped")
            continue
        ha, hb = sha(a), sha(b)
        A = Comp(dict(path=a, weights=I.W)).g.astype(np.float64)
        B = Comp(dict(path=b, weights=I.W)).g.astype(np.float64)
        print(f"\n  {fn}")
        print(f"    file sha16   {pa} {ha}   {pb} {hb}   "
              f"{'SAME' if ha == hb else 'DIFFER'}")
        if A.shape != B.shape:
            print(f"    DECODED SHAPES DIFFER {A.shape} vs {B.shape} -- "
                  f"the two pins do not produce comparable rasters")
            worst = float("inf")
            continue
        d = np.abs(A - B)
        lev = float(A.mean())
        # Not a mean-only assertion: ORCH's warning is that a defect can live
        # at the borders of a field whose mean is clean, so the max and the
        # count of differing pixels are printed alongside it.
        nz = int((d > 0).sum())
        print(f"    decoded {A.shape}  level {lev:.1f}")
        print(f"    identical pixels: {A.size - nz} of {A.size}  "
              f"({100.0 * (A.size - nz) / A.size:.4f}%)")
        print(f"    |diff|  mean {d.mean():.6g}  max {d.max():.6g}  "
              f"max/level {d.max() / lev:.3e}")
        worst = max(worst, float(d.max() / lev))
    print("\n" + "=" * 100)
    if worst == 0.0:
        print("  The two pins produce BIT-IDENTICAL decoded pixels on this subject.")
        print("  sec.9's 119 reading and the M115 ladder are on one binary for")
        print("  measurement purposes and may be discussed together.")
    else:
        print(f"  The two pins DIFFER, worst {worst:.3e} of level.  Sec.9's 119")
        print("  reading and this ladder are NOT on one binary; the ladder stands")
        print("  alone and no digit may be carried between them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
