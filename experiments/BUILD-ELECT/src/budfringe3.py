"""ORCH's bud rim, take 3: boundary-tracked, control-differenced, no rail.

Take 2's own control convicted take 2. Reading its output:

    CONTROL, 300 px into empty backdrop, no silhouette:
      DEFAULT  p95 over = 384 DN        on-edge p95 = 499 DN
      CA-OFF   p95 over = 471 DN        on-edge p95 = 901 DN

  The default arm's on-edge value was barely above its own backdrop. Two
  defects, both mine:

  (a) `over = peak - max(shoulder)` is a MAXIMUM over ~25 noisy samples minus a
      median. Its expectation is strictly positive on pure noise, so the
      statistic CANNOT return zero and a null is not expressible in it. Fixed
      two ways: a 3 px median along the transect before the peak, and every
      value reported as a DIFFERENCE against the same statistic measured in
      backdrop on the same rows -- so the noise bias cancels instead of being
      argued away.

  (b) the silhouette is CURVED and take 2 walked a FIXED COLUMN down 200 rows.
      Most of those rows never crossed the boundary, so the "distribution over
      the boundary" was mostly a distribution over empty backdrop. Fixed by
      tracking the green edge per row.

  Take 2 also RAILED both n=1 arms at its +/-16 search limit and printed them
  UNUSABLE. That guard worked and is kept, but the limit is the problem: the n=1
  renders carry a different coverage crop. Registration is now phase
  correlation, which has no search bound, and the NCC at the solved shift is
  printed beside the NCC at zero so an improvement is visible rather than
  assumed.

WHAT TAKE 2 DID ESTABLISH, and take 3 must either confirm or kill:
  the two n=205 arms register at (0,0) with ncc 1.000 -- they are pixel-aligned,
  same frames, same alignment solve, single variable -- and `--fix-ca off` had
  the LARGER overshoot, 1291 DN against the default's 639. If that holds, the
  lateral-CA correction is HALVING this rim, not causing it, and my own hypothesis
  is refuted in the direction I proposed it.

Orientation is measured, not assumed: green level on both shoulders is printed,
so which side is bud and which is blown backdrop is read off the data.

DEFECT FOUND IN THIS FILE'S OWN FIRST RUN, recorded rather than quietly fixed:
the border mask was written `gx[:REGWIN] = gx[-REGWIN:] = 0` with REGWIN 512 on
an 800 px tile. The two slices OVERLAP, so every row and column was zeroed and
the whole gradient map was zero. `np.argmax` of an all-zero array returns 0
without complaint, so the "site chosen on green gradient" was the tile ORIGIN --
flat backdrop, green 20981 vs 21037 across it, no silhouette anywhere near. The
run printed a full table of rim amplitudes for four arms, including +1104 DN for
n=1 argmax, and every number was measured on empty sky.

Nothing in the output said "failed". This is the same shape as the other
failures on this project: the broken configuration emits exactly what the
working one emits. The margin is now REGWIN//2 + 8 (the real requirement, since
phase correlation needs half a window either side), and two guards below refuse
rather than return: the mask must leave candidate pixels, and the chosen site
must show a real green step.
"""
import os
import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
TILE_X, TILE_Y, TILE = 2864, 864, 800
HALF, SHOULDER = 12, 7
REGWIN = 512
NROW = 200
CTL_OFF = 300

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


def ncc_at(gref, gmov, cy, cx, dy, dx, h):
    a = gref[cy - h:cy + h, cx - h:cx + h].astype(np.float64)
    b = gmov[cy - h + dy:cy + h + dy, cx - h + dx:cx + h + dx].astype(np.float64)
    a, b = a - a.mean(), b - b.mean()
    d = np.sqrt((a * a).sum()) * np.sqrt((b * b).sum())
    return float((a * b).sum() / d) if d else 0.0


def phase_shift(gref, gmov, cy, cx):
    """Integer shift by phase correlation -- no search bound, so it cannot rail."""
    h = REGWIN // 2
    a = gref[cy - h:cy + h, cx - h:cx + h].astype(np.float64)
    b = gmov[cy - h:cy + h, cx - h:cx + h].astype(np.float64)
    a, b = a - a.mean(), b - b.mean()
    win = np.hanning(REGWIN)[:, None] * np.hanning(REGWIN)[None, :]
    A, B = np.fft.rfft2(a * win), np.fft.rfft2(b * win)
    R = A * np.conj(B)
    m = np.abs(R)
    R = np.where(m > 0, R / np.maximum(m, 1e-12), 0)
    c = np.fft.irfft2(R, s=(REGWIN, REGWIN))
    dy, dx = np.unravel_index(int(np.argmax(c)), c.shape)
    if dy > REGWIN // 2:
        dy -= REGWIN
    if dx > REGWIN // 2:
        dx -= REGWIN
    return int(dy), int(dx), float(c.max())


def med3(v):
    return np.median(np.stack([np.roll(v, -1), v, np.roll(v, 1)]), axis=0)


def over_at(rgv, x):
    lo = HALF + SHOULDER
    seg = rgv[x - lo:x + lo + 1]
    return float(seg.max()) - max(float(np.median(rgv[x - lo:x - HALF + 1])),
                                  float(np.median(rgv[x + HALF:x + lo + 1])))


def main():
    print("=" * 78)
    print("BUD RIM, take 3 -- boundary-tracked, control-differenced")
    print("=" * 78)
    ref = load(REF)
    H, W = ref.shape[:2]
    gref = ref[:, :, 1]

    g = gref[TILE_Y:TILE_Y + TILE, TILE_X:TILE_X + TILE].astype(np.float64)
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
    m = REGWIN // 2 + 8
    assert 2 * m < TILE, f"margin {m} would zero the whole {TILE}px tile"
    keep = np.zeros_like(gx, bool)
    keep[m:TILE - m, m:TILE - m] = True
    gx = np.where(keep, gx, 0.0)
    n_cand = int(keep.sum())
    assert n_cand > 0 and gx.max() > 0, (
        f"site search has no candidates ({n_cand} px, max grad {gx.max()}) -- "
        "refusing rather than returning argmax of an all-zero array")
    sy, sx = np.unravel_index(int(np.argmax(gx)), gx.shape)
    CY, CX = TILE_Y + sy, TILE_X + sx
    print(f"  site search: {n_cand} candidate px, max |grad G| = "
          f"{gx[sy, sx]:.0f} DN/px")
    r = np.hypot(CY - H / 2.0, CX - W / 2.0)
    print(f"  site (green gradient) abs ({CX},{CY}); radius {r:.0f} px; "
          f"predicted CA R-vs-G shift {r * 704.5e-6:.2f} px")
    gl = float(np.median(gref[CY - 1:CY + 2, CX - 30:CX - 15]))
    gr = float(np.median(gref[CY - 1:CY + 2, CX + 15:CX + 30]))
    step = abs(gl - gr)
    print(f"  orientation MEASURED: green left {gl:.0f} DN, right {gr:.0f} DN, "
          f"step {step:.0f} -> {'bud LEFT' if gl < gr else 'bud RIGHT'}")
    assert step > 2000, (
        f"green step across the site is only {step:.0f} DN -- this is not a "
        "silhouette. Refusing: take 3's first run measured flat backdrop and "
        "reported it as a rim.")
    print()

    print(f"  {'arm':<40} {'dy':>4} {'dx':>4} {'ncc0':>6} {'ncc*':>6} "
          f"{'edge':>7} {'ctl':>7} {'EDGE-CTL':>9}")
    out = []
    for name, fn in ARMS:
        p = os.path.join(OUT, fn)
        if not os.path.exists(p):
            print(f"  {name:<40} MISSING -- skipped, NOT a pass")
            continue
        a = ref if fn == REF else load(fn)
        if fn == REF:
            dy = dx = 0
            n0 = nstar = 1.0
        else:
            dy, dx, _ = phase_shift(gref, a[:, :, 1], CY, CX)
            n0 = ncc_at(gref, a[:, :, 1], CY, CX, 0, 0, REGWIN // 2)
            nstar = ncc_at(gref, a[:, :, 1], CY, CX, dy, dx, REGWIN // 2)
        ga = a[:, :, 1]
        ed, ct = [], []
        xprev = CX + dx
        for yy in range(CY + dy - NROW // 2, CY + dy + NROW // 2):
            win = ga[yy, xprev - 25:xprev + 26].astype(np.float64)
            xe = xprev - 25 + int(np.argmax(np.abs(np.diff(win, prepend=win[:1]))))
            xprev = xe
            band = a[yy - 1:yy + 2, :, :].astype(np.float64).mean(0)
            rgv = med3(band[:, 0] - band[:, 1])
            ed.append(over_at(rgv, xe))
            ct.append(over_at(rgv, xe + CTL_OFF))
        e95, c95 = np.percentile(ed, 95), np.percentile(ct, 95)
        print(f"  {name:<40} {dy:>4} {dx:>4} {n0:>6.3f} {nstar:>6.3f} "
              f"{e95:>7.0f} {c95:>7.0f} {e95 - c95:>9.0f}")
        out.append((name, e95 - c95, nstar))
        if fn != REF:
            del a

    print()
    print("  EDGE-CTL is the rim above the SAME statistic in empty backdrop on")
    print("  the SAME rows, so the positive bias of a max-over-noise cancels.")
    print()
    print("  VERDICT")
    for name, d, nstar in out:
        q = "unreliable, poor registration" if nstar < 0.9 else ""
        print(f"    {name:<40} rim = {d:+7.0f} DN   {q}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
