"""Take 7: sweep the averaging, because it is the property that decides sensitivity.

Take 6 averaged 81 edge-aligned rows to beat down noise, and the rim shrank:
ORCH read peak +22 against interior +11 on a single row, take 6 read peak 12.5
against interior 10.3 -- OVER 2.2 where ORCH had ~11. That is ORCH's OWN failure
#1 reproduced in my instrument: "the rim is confined to a few edges; averaging
over all of them diluted it away."

So the number of averaged rows trades noise against dilution, and it is exactly
the fleet's standing question -- what property of the input decides whether this
check can see anything, and have I varied it? Take 6 picked 81 and did not vary
it. This sweeps it.

Read the two columns TOGETHER at each N:
  * CTL is measured on ORCH's flat background rows with identical treatment, so
    it is the noise floor of the statistic at that N and should fall as 1/sqrt(N).
  * If OVER falls at the same rate as CTL, the rim is being averaged away and
    the useful setting is small N.
  * If OVER holds while CTL falls, the rim is coherent along the boundary and
    large N is correct.
  * OVER/CTL is the discriminating ratio, and the N that maximises it is the
    honest operating point -- reported here as a grid, not as a chosen number,
    so the limit can be audited rather than trusted.

ORCH's own rows already predict dilution: their over-interior excess ran +11,
+5, +5 at rows 40, 60, 90. It is not constant along the boundary.
"""
import os
import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
SHIP = r"C:\dev\strehl-out\SHIP-V2"
SX, SY, CTL_Y = 3328, 924, 1004
SPAN, TRACK = 60, 12
GRID = (0, 2, 5, 10, 20, 40)

ARMS = [
    ("ORCH master  g4.5 sRGB", os.path.join(
        SHIP, "flower-bud-alone-cpl--SHIP-V2.tiff"), True),
    ("g2.0 LINEAR (the default)", os.path.join(OUT, "fb-noflags.tiff"), False),
    ("g2.0 LINEAR --fix-ca off", os.path.join(OUT, "fb-caoff.tiff"), False),
    ("n=1 pyramid (NO election)", os.path.join(OUT, "one-fb-pyramid.tiff"), False),
]


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: expected uint16, got {a.dtype}"
    return a[:, :, :3]


def esf(a, y0, x0, srgb, track, nrow):
    s = 257.0 if srgb else 1.0
    rg = []
    xp = x0
    for y in range(y0 - nrow, y0 + nrow + 1):
        band = a[y - 1:y + 2, :, :].astype(np.float64).mean(0) / s
        if track:
            w = band[xp - TRACK:xp + TRACK + 1, 1]
            xp = xp - TRACK + int(np.argmax(np.abs(np.diff(w, prepend=w[:1]))))
        xe = xp if track else x0
        rg.append(band[xe - SPAN:xe + SPAN + 1, 0] - band[xe - SPAN:xe + SPAN + 1, 1])
    return np.mean(rg, axis=0)


def over_of(p):
    c = SPAN
    inter = float(np.median(p[c - 60:c - 30]))
    back = float(np.median(p[c + 35:c + 60]))
    return float(p[c - 15:c + 16].max()) - max(inter, back)


def main():
    print("=" * 78)
    print("TAKE 7 -- averaging sweep. OVER vs its own noise floor CTL.")
    print("=" * 78)
    print("  N = rows either side; 1 row at N=0, 81 rows at N=40.")
    for name, path, srgb in ARMS:
        if not os.path.exists(path):
            print(f"\n  {name}: MISSING -- skipped, NOT a pass")
            continue
        a = load(path)
        u = "8bit" if srgb else "DN"
        print(f"\n  {name}   [{u}]")
        print(f"    {'N':>4} {'rows':>5} {'OVER':>8} {'CTL':>8} {'OVER/CTL':>9}")
        for n in GRID:
            ov = over_of(esf(a, SY, SX, srgb, True, n))
            ct = over_of(esf(a, CTL_Y, SX, srgb, False, n))
            rr = ov / ct if abs(ct) > 1e-9 else float("nan")
            print(f"    {n:>4} {2*n+1:>5} {ov:>8.1f} {ct:>8.1f} {rr:>9.2f}")
        del a
    print()
    print("  A rim that survives averaging is coherent along the boundary.")
    print("  A rim that decays with N at the same rate as CTL is local, and any")
    print("  single large-N number understates it -- which is how take 6 turned")
    print("  ORCH's +11 into +2.2 without either value being wrong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
