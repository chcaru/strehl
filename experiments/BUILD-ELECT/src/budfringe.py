"""ORCH's bud rim: is it the election, or the lateral-CA resample?

ORCH measured a chromatic OVERSHOOT on the bud silhouette -- R-G peaks at +22
against an interior of +11 and a background of -4, so it exceeds both endpoints
and cannot be an alpha blend of them. Their hypothesis is per-channel election.

Two things ORCH did not have when they wrote that:

  1. The default render banner says
       lateral CA : CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl" (default on)
     A lateral-CA correction is a RADIAL PER-CHANNEL RESAMPLE -- it rescales R
     against G by eps_R = -704.5 ppm. Any negative-lobe interpolation kernel
     rings, and a channel that is resampled while another is not rings
     DIFFERENTIALLY. That produces an R-G peak exceeding both endpoints, on a
     diffuse edge, with no election involved at all.

  2. `--fix-ca off` exists, and n=1 renders exist. Between them the two
     candidate mechanisms are separable:

       arm                     election live?   CA resample live?
       n=1 argmax              NO               yes
       n=1 pyramid             NO               yes
       n=205 default           yes              yes
       n=205 --fix-ca off      yes              NO

PRE-REGISTERED, before looking (ORCH asked for this explicitly):
  * If the overshoot survives at n=1, THE ELECTION HYPOTHESIS IS DEAD for this
    subject -- there is no election in a one-frame render.
  * If the overshoot collapses under --fix-ca off, the cause is the CA resample.
  * If it survives BOTH, it is neither, and the cause is downstream (demosaic,
    tone/highlight path).
  * If it vanishes at n=1 AND survives --fix-ca off, ORCH is right and it is
    the election.

THREE FAILURES ORCH REPORTED, AND HOW THIS AVOIDS EACH:
  * they averaged over the whole silhouette and diluted it away
      -> no averaging along the boundary; per-row transects at one site.
  * a luma-gradient gate returned edge px = 0 on a pale bud against white
      -> NO luma gate anywhere in this file. The site is found by the chroma
         overshoot itself.
  * min(R-G, B-G) scored 0.00% because the rim is red-dominant with B BELOW G
      -> R-G and B-G are reported SEPARATELY and SIGNED. No hue assumption.

Measured on LINEAR camera-native TIFFs, never on an sRGB viewing render, so the
amplitudes here are not comparable to ORCH's sRGB numbers -- only the SHAPE
(peak vs both endpoints) is, and shape is what the argument rests on. R/G is
also reported because it is invariant to exposure and to any gain applied
equally to both channels.
"""
import os
import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
TILE_X, TILE_Y, TILE = 2864, 864, 800
HALF = 12           # transect half-width for the "exceeds both endpoints" test
SHOULDER = 7        # how many px of each shoulder to median

ARMS = [
    ("n=1 argmax   (no election, no pyramid)", f"{OUT}\\one-fb-argmax.tiff", False, True),
    ("n=1 pyramid  (no election)", f"{OUT}\\one-fb-pyramid.tiff", False, True),
    ("n=205 DEFAULT (election + CA)", f"{OUT}\\fb-noflags.tiff", True, True),
    ("n=205 --fix-ca off (election, NO CA)", f"{OUT}\\fb-caoff.tiff", True, False),
]


def tile_of(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    h, w = a.shape[:2]
    t = a[TILE_Y:TILE_Y + TILE, TILE_X:TILE_X + TILE, :3].astype(np.int32)
    del a
    return t, (h, w)


def overshoot_map(rg):
    """over(y,x) = (R-G) minus the larger of its two shoulders, HALF px away.

    Positive means the pixel exceeds BOTH neighbourhoods, which is exactly the
    property ORCH's argument turns on and which no mixture can produce.
    """
    lo = HALF + SHOULDER
    n = rg.shape[1]
    out = np.full(rg.shape, -10**6, np.float64)
    for x in range(lo, n - lo):
        left = np.median(rg[:, x - lo:x - HALF + 1], axis=1)
        right = np.median(rg[:, x + HALF:x + lo + 1], axis=1)
        out[:, x] = rg[:, x] - np.maximum(left, right)
    return out


def main():
    have = [(n, p, e, c) for (n, p, e, c) in ARMS if os.path.exists(p)]
    missing = [p for (_, p, _, _) in ARMS if not os.path.exists(p)]
    print("=" * 78)
    print("ORCH's BUD RIM: election, or the lateral-CA resample?")
    print("=" * 78)
    for p in missing:
        print(f"  MISSING (skipped, NOT counted as a pass): {p}")

    # Locate the site ONCE, on the default arm, then read every arm at the same
    # coordinates. Locating per-arm would let each arm find its own best pixel
    # and would guarantee a positive everywhere.
    ref = [x for x in have if "DEFAULT" in x[0]]
    assert ref, "need the default arm to locate the site"
    t, shape = tile_of(ref[0][1])
    print(f"  master {shape[1]} x {shape[0]}, tile {TILE}x{TILE} at "
          f"({TILE_X},{TILE_Y})")
    rg = (t[:, :, 0] - t[:, :, 1]).astype(np.float64)
    sm = np.stack([np.roll(rg, k, axis=0) for k in (-1, 0, 1)]).mean(0)
    ov = overshoot_map(sm)
    ov[:3, :] = ov[-3:, :] = -10**6
    y, x = np.unravel_index(int(np.argmax(ov)), ov.shape)
    print(f"  strongest R-G overshoot in the tile: row {y}, col {x} "
          f"(absolute {TILE_X + x},{TILE_Y + y}), over = {ov[y, x]:.0f} DN")

    cy, cx = shape[0] / 2.0, shape[1] / 2.0
    r = np.hypot(TILE_Y + y - cy, TILE_X + x - cx)
    rmax = np.hypot(cy, cx)
    print(f"  radius from frame centre: {r:.0f} px = {100 * r / rmax:.0f}% of "
          f"the corner (lateral CA is ZERO on axis and grows with this)")
    del t, rg, sm, ov

    print()
    print(f"  {'arm':<40} {'interior':>9} {'PEAK':>7} {'backdrop':>9} "
          f"{'over':>7} {'B-G pk':>7}")
    res = {}
    for name, path, elect, ca in have:
        t, _ = tile_of(path)
        row = t[y - 1:y + 2, :, :].astype(np.float64).mean(0)
        rgv, bgv = row[:, 0] - row[:, 1], row[:, 2] - row[:, 1]
        lo = HALF + SHOULDER
        seg = rgv[x - lo:x + lo + 1]
        peak = float(seg.max())
        interior = float(np.median(rgv[x - lo:x - HALF + 1]))
        backdrop = float(np.median(rgv[x + HALF:x + lo + 1]))
        over = peak - max(interior, backdrop)
        res[name] = (interior, peak, backdrop, over, float(bgv[x]))
        print(f"  {name:<40} {interior:>9.0f} {peak:>7.0f} {backdrop:>9.0f} "
              f"{over:>7.0f} {bgv[x]:>7.0f}")
        del t

    print()
    print("  R-G TRANSECT, linear DN, default arm vs --fix-ca off:")
    for name, path, _, _ in have:
        t, _ = tile_of(path)
        row = t[y - 1:y + 2, :, :].astype(np.float64).mean(0)
        rgv = row[:, 0] - row[:, 1]
        s = " ".join(f"{rgv[xx]:+5.0f}" for xx in range(x - 14, x + 15))
        print(f"    {name[:38]:<38} {s}")
        del t

    print()
    print("  VERDICT INPUTS (pre-registered above, not chosen after the fact)")
    for name in res:
        i, p, b, o, _ = res[name]
        exceeds = p > i and p > b
        print(f"    {name:<40} exceeds both endpoints: "
              f"{'YES' if exceeds else 'no ':>3}  (over {o:+.0f} DN)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
