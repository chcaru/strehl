"""ORCH's rim, take 6: edge-aligned averaging, matched control, and a repro census.

Take 5 produced one clean result and one disqualifying one.

  CLEAN: ORCH's master and my current-binary render at their exact argv read
  12.7 / 17.3 / 4.6 / 4.6 / 6.7 / 0.8 -- the same to every printed decimal.

  DISQUALIFYING: the control was not quiet. On ORCH's own flat background row,
  the statistic read 70-2229 DN in the linear arms. `--fix-ca off` gave
  CTL 2228.7 against OVER 256.5 -- the control LARGER than the signal -- and
  n=1 gave CTL 1200.0 against OVER -62.5. Those two rows measured noise.

Why: OVER is a MAX over 41 samples minus a median, taken on a 3-row mean. In a
bright linear background the per-pixel noise is large in DN, so the max is large
regardless of any rim. The sRGB arms looked fine only because the tone curve
compresses the background, which is not a reason to trust sRGB -- it is the same
statistic with its noise hidden.

The fix is not a different space, it is more samples. This builds an EDGE SPREAD
FUNCTION: for each of 81 rows the green edge is located, each row's transect is
shifted to put its own edge at offset 0, and the aligned transects are AVERAGED.
The rim survives because alignment preserves it; the noise falls as sqrt(81).
The control gets the identical treatment on ORCH's flat rows, so both sides of
the comparison carry the same noise reduction and the difference means something.

Alignment is by integer row shift only -- no interpolation -- because a
sub-pixel resample would blur the 1-3 px feature under test.

ALSO CORRECTED HERE: take 5 let me write that the binary "is not a variable" on
the strength of a table agreeing to one decimal at ONE SITE. The files are NOT
byte-identical: C9312ACB... vs CF4DDAD2..., and they differ in SIZE, 198023555
vs 198026320 bytes. Agreement at one address is not agreement, so section 1
counts the differing pixels instead of asserting anything.

AND CORRECTED: take 5's "G dip" was green-at-peak minus green 30-60 px into the
interior. Green climbs steadily toward the bright backdrop over that span, so
the statistic was dominated by the ramp and came out POSITIVE in every arm --
reporting "no dip" for a feature ORCH's own transect plainly shows (G runs
...145 143 142 141 140 137 137 139 144 155..., a local minimum of 137). It is
now measured against the LOCAL plateau just inside the edge, which is what the
word "dip" meant.
"""
import os
import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
SHIP = r"C:\dev\strehl-out\SHIP-V2"
SX, SY, CTL_Y = 3328, 924, 1004
NROW, SPAN, TRACK = 40, 60, 12

ARMS = [
    ("ORCH master g4.5 sRGB pin b9b6921e", os.path.join(
        SHIP, "flower-bud-alone-cpl--SHIP-V2.tiff"), True),
    ("mine        g4.5 sRGB current bin", os.path.join(OUT, "fb-g45-srgb.tiff"), True),
    ("mine        g4.5 LINEAR", os.path.join(OUT, "fb-g45-lin.tiff"), False),
    ("mine        g2.0 LINEAR (default)", os.path.join(OUT, "fb-noflags.tiff"), False),
    ("mine        g2.0 LIN --fix-ca off", os.path.join(OUT, "fb-caoff.tiff"), False),
    ("mine        n=1 pyramid NO election", os.path.join(OUT, "one-fb-pyramid.tiff"), False),
    ("mine        n=1 argmax  NO election", os.path.join(OUT, "one-fb-argmax.tiff"), False),
]


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: expected uint16, got {a.dtype}"
    return a[:, :, :3]


def esf(a, y0, x0, srgb, track):
    """Edge-aligned mean transect. track=False pins x (for the flat control)."""
    s = 257.0 if srgb else 1.0
    rg, gg = [], []
    xp = x0
    for y in range(y0 - NROW, y0 + NROW + 1):
        band = a[y - 1:y + 2, :, :].astype(np.float64).mean(0) / s
        if track:
            w = band[xp - TRACK:xp + TRACK + 1, 1]
            xe = xp - TRACK + int(np.argmax(np.abs(np.diff(w, prepend=w[:1]))))
            xp = xe
        else:
            xe = x0
        rg.append(band[xe - SPAN:xe + SPAN + 1, 0] - band[xe - SPAN:xe + SPAN + 1, 1])
        gg.append(band[xe - SPAN:xe + SPAN + 1, 1])
    return np.mean(rg, axis=0), np.mean(gg, axis=0)


def stat(p):
    c = SPAN
    inter = float(np.median(p[c - 60:c - 30]))
    back = float(np.median(p[c + 35:c + 60]))
    seg = p[c - 15:c + 16]
    pk = float(seg.max())
    return inter, pk, back, pk - max(inter, back), c - 15 + int(np.argmax(seg))


def main():
    print("=" * 78)
    print("TAKE 6 -- edge-aligned averaging (81 rows), matched control")
    print("=" * 78)

    m = os.path.join(SHIP, "flower-bud-alone-cpl--SHIP-V2.tiff")
    r = os.path.join(OUT, "fb-g45-srgb.tiff")
    if os.path.exists(m) and os.path.exists(r):
        A, B = load(m), load(r)
        print(f"  1. REPRODUCTION CENSUS  master {A.shape} vs mine {B.shape}")
        if A.shape == B.shape:
            d = np.abs(A.astype(np.int32) - B.astype(np.int32))
            nz = int((d > 0).sum())
            print(f"     differing samples : {nz:,} of {d.size:,} "
                  f"({100.0 * nz / d.size:.4f}%)   max delta {int(d.max())} DN")
            t = d[SY - 200:SY + 200, SX - 200:SX + 200]
            print(f"     in the rim tile   : {int((t > 0).sum()):,} of {t.size:,} "
                  f"({100.0 * (t > 0).mean():.4f}%)  max delta {int(t.max())} DN")
        else:
            print("     SHAPES DIFFER -- not comparable pixelwise")
        del A, B

    print()
    print(f"  2. RIM, edge-aligned. {2*NROW+1} rows averaged; control identical.")
    print(f"  {'arm':<36} {'inter':>7} {'PEAK':>7} {'back':>7} {'OVER':>7} "
          f"{'CTL':>7} {'Gdip':>7} {'unit':>5}")
    for name, path, srgb in ARMS:
        if not os.path.exists(path):
            print(f"  {name:<36} MISSING -- skipped, NOT a pass")
            continue
        a = load(path)
        pr, pg = esf(a, SY, SX, srgb, True)
        i, pk, b, ov, k = stat(pr)
        cr, _ = esf(a, CTL_Y, SX, srgb, False)
        _, _, _, cov, _ = stat(cr)
        plateau = float(np.median(pg[SPAN - 25:SPAN - 12]))
        gdip = float(pg[k]) - plateau
        print(f"  {name:<36} {i:>7.1f} {pk:>7.1f} {b:>7.1f} {ov:>7.1f} "
              f"{cov:>7.1f} {gdip:>7.1f} {'8bit' if srgb else 'DN':>5}")
        del a

    print()
    print("  OVER must be read against CTL on the SAME line: both now carry the")
    print("  same sqrt(81) noise reduction, so OVER >> CTL is a real rim and")
    print("  OVER ~ CTL is not. Gdip < 0 means green FALLS at the rim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
