"""The control take 7's n=1 result needs before it can mean anything.

Take 7's sweep says the n=1 arm has NO overshoot -- OVER negative at 5 of its 6
averaging settings, against a positive OVER at every small N for all three
n=205 arms. Read naively that revives ORCH's election hypothesis: the effect
needs the merge.

There is an obvious confound and it must be killed first. `one-fb-pyramid.tiff`
is ONE frame from a 205-frame focus bracket. If the bud silhouette is not in
focus in that particular frame, there is no sharp edge there, and a soft edge
CANNOT ring no matter what the reconstruction does. The absence of an overshoot
would then say nothing whatever about election -- it would say the edge was
blurred.

So measure the edge itself. The green edge-spread function is built exactly as
take 6/7 build it, and its 10-90% rise distance is the sharpness of the very
feature whose ringing is under test.

  * If n=1's rise is comparable to n=205's, the edge is present and sharp in the
    single frame, the confound is dead, and take 7's null is about election.
  * If n=1's rise is much longer, the single frame is defocused here and the
    n=1 arms must be withdrawn from the argument entirely.

This is the check whose result I cannot predict, which is why it is worth
running: it can invalidate the most interesting number I have.
"""
import os
import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
SHIP = r"C:\dev\strehl-out\SHIP-V2"
SX, SY = 3328, 924
SPAN, TRACK, NROW = 60, 12, 20

ARMS = [
    ("ORCH master  g4.5 sRGB", os.path.join(
        SHIP, "flower-bud-alone-cpl--SHIP-V2.tiff"), True),
    ("g2.0 LINEAR (the default)", os.path.join(OUT, "fb-noflags.tiff"), False),
    ("g2.0 LINEAR --fix-ca off", os.path.join(OUT, "fb-caoff.tiff"), False),
    ("n=1 pyramid (NO election)", os.path.join(OUT, "one-fb-pyramid.tiff"), False),
    ("n=1 argmax  (NO election)", os.path.join(OUT, "one-fb-argmax.tiff"), False),
]


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: expected uint16, got {a.dtype}"
    return a[:, :, :3]


def green_esf(a, srgb):
    s = 257.0 if srgb else 1.0
    g = []
    xp = SX
    for y in range(SY - NROW, SY + NROW + 1):
        band = a[y - 1:y + 2, :, :].astype(np.float64).mean(0) / s
        w = band[xp - TRACK:xp + TRACK + 1, 1]
        xp = xp - TRACK + int(np.argmax(np.abs(np.diff(w, prepend=w[:1]))))
        g.append(band[xp - SPAN:xp + SPAN + 1, 1])
    return np.mean(g, axis=0)


def rise_1090(p):
    lo = float(np.median(p[:20]))
    hi = float(np.median(p[-20:]))
    if hi <= lo:
        return float("nan"), lo, hi
    t10, t90 = lo + 0.10 * (hi - lo), lo + 0.90 * (hi - lo)
    idx = np.where((p >= t10) & (p <= t90))[0]
    return (float(idx.max() - idx.min() + 1) if len(idx) else float("nan")), lo, hi


def main():
    print("=" * 78)
    print("EDGE SHARPNESS CONTROL -- can the n=1 frame ring at all?")
    print("=" * 78)
    print(f"  green ESF at ABS ({SX},{SY}), {2*NROW+1} rows, edge-aligned")
    print()
    print(f"  {'arm':<30} {'10-90% rise':>12} {'low':>9} {'high':>9} "
          f"{'contrast':>9}")
    for name, path, srgb in ARMS:
        if not os.path.exists(path):
            print(f"  {name:<30} MISSING -- skipped, NOT a pass")
            continue
        a = load(path)
        p = green_esf(a, srgb)
        w, lo, hi = rise_1090(p)
        print(f"  {name:<30} {w:>10.1f} px {lo:>9.0f} {hi:>9.0f} "
              f"{hi - lo:>9.0f}")
        del a
    print()
    print("  A longer rise means a softer edge. If the n=1 rows are much softer")
    print("  than the n=205 rows, take 7's n=1 null is about DEFOCUS, not about")
    print("  election, and the n=1 arms come out of the argument.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
