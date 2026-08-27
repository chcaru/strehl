"""ORCH's bud rim, take 2: registered, and with the site chosen off GREEN.

Take 1 (budfringe.py) produced numbers I discarded. Its own output showed why:

  * the site was located on the DEFAULT arm's own strongest R-G overshoot and
    every other arm was then read at those coordinates -- an argmax on one arm
    scored against arms that did not choose it;
  * the arms are NOT registered. The n=1 transect's edge sat ~22 px right of the
    n=205 transect's edge, so identical coordinates addressed different scene
    content and the n=1 comparison measured nothing;
  * the auto-found site was ~230 px from ORCH's stated sub-region, so it may not
    even have been their rim.

Fixes, in order:

  1. REGISTER. Integer-shift only, never sub-pixel: a resample would add blur to
     an experiment whose entire subject is a 1 px channel displacement. The
     shift is solved on the GREEN channel, because lateral CA moves R and B
     against a STATIONARY G -- registering on green means the effect under test
     cannot drive its own alignment. Window is small (160 px) so that a coverage
     SCALE difference between arms contributes under half a pixel across it.
     The solved shift is printed for every arm; if it rails at the search limit
     the arm is reported unusable rather than silently misregistered.

  2. CHOOSE THE SITE OFF GREEN, not off R-G. The boundary is where the green
     channel steps. That is arm-neutral with respect to the chromatic quantity
     being compared.

  3. REPORT A DISTRIBUTION, not one pixel. ORCH's first failure was averaging
     over the whole silhouette and diluting the rim away; the fix is a high
     PERCENTILE over many boundary sites, which neither dilutes nor cherry-picks.

NOTE ON ORCH'S "LOW LUMA CONTRAST" -- their luma-gradient gate returned edge
px = 0 because they gated an 8-bit sRGB PNG, where a pale bud against near-white
is compressed into a few codes. In LINEAR DN the same edge is a large step. The
blindness was in the encoding, not in the scene.

PRE-REGISTERED, unchanged from take 1:
  * overshoot survives at n=1  -> election hypothesis DEAD (no election exists
    in a one-frame render);
  * overshoot collapses under --fix-ca off -> cause is the CA resample;
  * survives both -> neither; cause is downstream;
  * gone at n=1 and present with --fix-ca off -> ORCH is right, it is election.
"""
import os
import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
TILE_X, TILE_Y, TILE = 2864, 864, 800
HALF, SHOULDER = 12, 7
SEARCH = 16          # integer shift search radius, px
REGWIN = 160         # registration window, px

ARMS = [
    ("n=205 DEFAULT (election + CA)", "fb-noflags.tiff"),
    ("n=205 --fix-ca off (election, NO CA)", "fb-caoff.tiff"),
    ("n=1 pyramid  (NO election)", "one-fb-pyramid.tiff"),
    ("n=1 argmax   (NO election, no pyramid)", "one-fb-argmax.tiff"),
]
REF = "fb-noflags.tiff"


def load(name):
    a = tifffile.imread(os.path.join(OUT, name))
    assert a.dtype == np.uint16, f"{name}: expected uint16, got {a.dtype}"
    return a[:, :, :3]


def solve_shift(gref, gmov, cy, cx):
    """Integer (dy,dx) maximising normalised cross-correlation of green."""
    h = REGWIN // 2
    a = gref[cy - h:cy + h, cx - h:cx + h].astype(np.float64)
    a = a - a.mean()
    na = np.sqrt((a * a).sum())
    best, bdy, bdx = -2.0, 0, 0
    for dy in range(-SEARCH, SEARCH + 1):
        for dx in range(-SEARCH, SEARCH + 1):
            b = gmov[cy - h + dy:cy + h + dy, cx - h + dx:cx + h + dx]
            b = b.astype(np.float64)
            b = b - b.mean()
            nb = np.sqrt((b * b).sum())
            if nb == 0:
                continue
            c = float((a * b).sum() / (na * nb))
            if c > best:
                best, bdy, bdx = c, dy, dx
    return bdy, bdx, best


def overshoot_row(rgv, x):
    lo = HALF + SHOULDER
    seg = rgv[x - lo:x + lo + 1]
    peak = float(seg.max())
    interior = float(np.median(rgv[x - lo:x - HALF + 1]))
    backdrop = float(np.median(rgv[x + HALF:x + lo + 1]))
    return interior, peak, backdrop, peak - max(interior, backdrop)


def main():
    print("=" * 78)
    print("BUD RIM, REGISTERED -- election vs lateral-CA resample")
    print("=" * 78)
    ref = load(REF)
    H, W = ref.shape[:2]
    gref = ref[:, :, 1]

    # --- site chosen off GREEN, inside the tile, nearest ORCH's sub-region ----
    ty, tx = slice(TILE_Y, TILE_Y + TILE), slice(TILE_X, TILE_X + TILE)
    g = gref[ty, tx].astype(np.float64)
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
    gx[:REGWIN, :] = gx[-REGWIN:, :] = 0
    gx[:, :REGWIN] = gx[:, -REGWIN:] = 0
    sy, sx = np.unravel_index(int(np.argmax(gx)), gx.shape)
    CY, CX = TILE_Y + sy, TILE_X + sx
    print(f"  master {W} x {H}; site chosen on GREEN gradient at "
          f"absolute ({CX},{CY}), |grad G| = {gx[sy, sx]:.0f} DN/px")
    r = np.hypot(CY - H / 2.0, CX - W / 2.0)
    rmax = np.hypot(H / 2.0, W / 2.0)
    eps = 704.5e-6
    print(f"  radius {r:.0f} px = {100 * r / rmax:.0f}% of corner; predicted "
          f"lateral-CA R vs G displacement = {r * eps:.2f} px")
    print()

    rows = []
    print(f"  {'arm':<40} {'dy':>3} {'dx':>3} {'ncc':>6} {'inter':>7} "
          f"{'PEAK':>7} {'back':>7} {'over':>7} {'p95 over':>9}")
    for name, fn in ARMS:
        p = os.path.join(OUT, fn)
        if not os.path.exists(p):
            print(f"  {name:<40} MISSING -- skipped, NOT a pass")
            continue
        a = ref if fn == REF else load(fn)
        dy, dx, ncc = (0, 0, 1.0) if fn == REF else solve_shift(
            gref, a[:, :, 1], CY, CX)
        railed = abs(dy) == SEARCH or abs(dx) == SEARCH
        band = a[CY + dy - 1:CY + dy + 2, :, :].astype(np.float64).mean(0)
        rgv = band[:, 0] - band[:, 1]
        i, pk, b, o = overshoot_row(rgv, CX + dx)
        # distribution: same statistic down 200 rows of the same boundary
        os_list = []
        for yy in range(CY + dy - 100, CY + dy + 100):
            bb = a[yy - 1:yy + 2, :, :].astype(np.float64).mean(0)
            rr = bb[:, 0] - bb[:, 1]
            os_list.append(overshoot_row(rr, CX + dx)[3])
        p95 = float(np.percentile(os_list, 95))
        flag = "  RAILED-UNUSABLE" if railed else ""
        print(f"  {name:<40} {dy:>3} {dx:>3} {ncc:>6.3f} {i:>7.0f} "
              f"{pk:>7.0f} {b:>7.0f} {o:>7.0f} {p95:>9.0f}{flag}")
        rows.append((name, o, p95, railed, ncc))
        if fn != REF:
            del a

    print()
    print("  CONTROL -- the same statistic 300 px INTO the backdrop, where there")
    print("  is no silhouette. A rim mechanism must be quiet here.")
    for name, fn in ARMS:
        p = os.path.join(OUT, fn)
        if not os.path.exists(p):
            continue
        a = ref if fn == REF else load(fn)
        dy, dx, _ = (0, 0, 1.0) if fn == REF else solve_shift(
            gref, a[:, :, 1], CY, CX)
        ctl = []
        for yy in range(CY + dy - 100, CY + dy + 100):
            bb = a[yy - 1:yy + 2, :, :].astype(np.float64).mean(0)
            ctl.append(overshoot_row(bb[:, 0] - bb[:, 1], CX + dx + 300)[3])
        print(f"    {name:<40} p95 over = {np.percentile(ctl, 95):>7.0f} DN")
        if fn != REF:
            del a

    print()
    print("  VERDICT INPUTS")
    for name, o, p95, railed, ncc in rows:
        if railed:
            print(f"    {name:<40} UNUSABLE (registration railed)")
        else:
            print(f"    {name:<40} over {o:+6.0f} DN, p95 {p95:+6.0f} DN "
                  f"(ncc {ncc:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
