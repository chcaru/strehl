"""ORCH's rim at ORCH's address: which variable actually makes it?

The distance-resolved profile (budfringe4.py) found NO R-G overshoot in the
current default and a large one with --fix-ca off. That was a real measurement
but it is not ORCH's artifact, because ORCH's master is CA-CORRECTED. Reading
its provenance:

  binary : acceptance-pins\\b9b6921e  (CF33AE08...), NOT the current 16EB215F
  argv   : stack ... --merge pyramid --pyramid-gate 4.5 --srgb --auto-exposure
  lateral CA : CORRECTING, gear matched, default on
  exposure   : +1.45 stops

So three variables separate my linear arms from theirs: GATE (4.5 vs the 2.00
default), COLOUR SPACE (sRGB at +1.45 stops vs linear), and BINARY. This ladder
moves one at a time.

It also stops aggregating. budfringe4 took a median over the WHOLE silhouette,
which is precisely ORCH's failure #1 -- a rim confined to part of the boundary
is diluted by the rest of it. ORCH's crop gives an exact address:

  asset flower-bud-alone-cpl--SHIP-V2--1to1.png is an 800x800 1:1 crop at tile
  origin (2864,864); their region is im[20:220, 350:560]; their peak is region
  (row 40, x 114) = asset (60,464) = ABSOLUTE (3328, 924).

Their row 120 lies entirely in background and stayed flat at -3..-7. That is
their built-in negative control and it is carried here as absolute row 1004: any
arm that shows a rim on THAT row is measuring something other than a silhouette.

WHAT ORCH'S OWN PIXELS SAY, which their report did not extract: the peak is not
a red excursion. Across their row 40, R runs 163 152 150 151 147 ... 159 while
G runs 152 153 150 151 147 145 143 142 141 140 137 137 139 144 155 166 -- G has
a local MINIMUM of 137 exactly where R-G peaks. The rim is a GREEN UNDERSHOOT,
deeper in G than in R. That is edge ringing with a channel-dependent amplitude,
and it predicts the effect should follow whatever controls band selection --
i.e. the GATE -- rather than the election.

A clipping explanation was tested and is DEAD: orchcheck.py measured 0.00% of
the region at >= 250 in every channel, max R 244 G 248 B 245, background
239/243/239. Nothing is pinned, so a per-channel ceiling cannot be bending the
difference.

sRGB arms are reported in 8-bit-equivalent units (/257) so they are directly
comparable with ORCH's numbers; linear arms in raw DN. The two are NOT
comparable with each other in amplitude and are not compared -- only the
presence and sign of an overshoot is.
"""
import os
import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
SHIP = r"C:\dev\strehl-out\SHIP-V2"
SX, SY = 3328, 924
CTL_Y = 1004
REGWIN = 512

ARMS = [
    ("ORCH master  g4.5 sRGB pin b9b6921e", os.path.join(
        SHIP, "flower-bud-alone-cpl--SHIP-V2.tiff"), True),
    ("mine         g4.5 sRGB current bin", os.path.join(OUT, "fb-g45-srgb.tiff"), True),
    ("mine         g4.5 LINEAR", os.path.join(OUT, "fb-g45-lin.tiff"), False),
    ("mine         g2.0 LINEAR (the default)", os.path.join(OUT, "fb-noflags.tiff"), False),
    ("mine         g2.0 LINEAR --fix-ca off", os.path.join(OUT, "fb-caoff.tiff"), False),
    ("mine         n=1 pyramid (NO election)", os.path.join(OUT, "one-fb-pyramid.tiff"), False),
]
REFI = 0


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: expected uint16, got {a.dtype}"
    return a[:, :, :3]


def shift_vs(gref, gmov, cy, cx):
    r = REGWIN // 2
    a = gref[cy - r:cy + r, cx - r:cx + r].astype(np.float64)
    b = gmov[cy - r:cy + r, cx - r:cx + r].astype(np.float64)
    a, b = a - a.mean(), b - b.mean()
    w = np.hanning(REGWIN)[:, None] * np.hanning(REGWIN)[None, :]
    A, B = np.fft.rfft2(a * w), np.fft.rfft2(b * w)
    R = A * np.conj(B)
    m = np.abs(R)
    c = np.fft.irfft2(np.where(m > 0, R / np.maximum(m, 1e-12), 0),
                      s=(REGWIN, REGWIN))
    dy, dx = np.unravel_index(int(np.argmax(c)), c.shape)
    dy = dy - REGWIN if dy > REGWIN // 2 else dy
    dx = dx - REGWIN if dx > REGWIN // 2 else dx
    b2 = gmov[cy - r + dy:cy + r + dy, cx - r + dx:cx + r + dx].astype(np.float64)
    b2 = b2 - b2.mean()
    n = float((a * b2).sum() /
              (np.sqrt((a * a).sum()) * np.sqrt((b2 * b2).sum())))
    return int(dy), int(dx), n


def readout(a, y, x, srgb):
    band = a[y - 1:y + 2, :, :].astype(np.float64).mean(0)
    s = 257.0 if srgb else 1.0
    rgv = (band[:, 0] - band[:, 1]) / s
    gv = band[:, 1] / s
    inter = float(np.median(rgv[x - 60:x - 30]))
    back = float(np.median(rgv[x + 40:x + 70]))
    seg = rgv[x - 20:x + 21]
    pk = float(seg.max())
    kx = x - 20 + int(np.argmax(seg))
    gdip = float(gv[kx]) - float(np.median(gv[x - 60:x - 30]))
    return inter, pk, back, pk - max(inter, back), kx, gdip


def main():
    print("=" * 78)
    print("ORCH's RIM AT ORCH'S ADDRESS -- one variable at a time")
    print("=" * 78)
    have = [(n, p, s) for (n, p, s) in ARMS if os.path.exists(p)]
    for n, p, _ in ARMS:
        if not os.path.exists(p):
            print(f"  MISSING (skipped, NOT a pass): {n}")
    ref = load(have[REFI][1])
    gref = ref[:, :, 1]
    print(f"  reference = {have[REFI][0]}, {ref.shape[1]} x {ref.shape[0]}")
    print(f"  site ABS ({SX},{SY}); ORCH's flat control row ABS y={CTL_Y}")
    print()
    print(f"  {'arm':<38} {'dy':>3} {'dx':>3} {'ncc':>6} {'inter':>7} "
          f"{'PEAK':>7} {'back':>7} {'OVER':>7} {'G dip':>7} {'CTL':>6}")
    for name, path, srgb in have:
        a = ref if path == have[REFI][1] else load(path)
        if path == have[REFI][1]:
            dy = dx = 0
            ncc = 1.0
        else:
            dy, dx, ncc = shift_vs(gref, a[:, :, 1], SY, SX)
        i, pk, b, ov, kx, gd = readout(a, SY + dy, SX + dx, srgb)
        _, _, _, cov, _, _ = readout(a, CTL_Y + dy, SX + dx, srgb)
        u = "8bit" if srgb else "DN"
        print(f"  {name:<38} {dy:>3} {dx:>3} {ncc:>6.3f} {i:>7.1f} "
              f"{pk:>7.1f} {b:>7.1f} {ov:>7.1f} {gd:>7.1f} {cov:>6.1f}  {u}")
        if path != have[REFI][1]:
            del a
    print()
    print("  OVER = peak R-G minus the larger of interior/background, i.e. the")
    print("  'exceeds both endpoints' quantity ORCH's argument rests on.")
    print("  G dip = green at the peak minus green in the interior. Negative")
    print("  means the rim is made by green FALLING, not red rising.")
    print("  CTL = the same OVER on ORCH's flat background row. It must be small;")
    print("  an arm with a large CTL is not measuring a silhouette.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
