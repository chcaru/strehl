"""Does `--photometric` reduce the merge's manufactured background structure?

This is the test pre-registered to M116 that M116 did not run. M116 scored the
photometric arm with a global sharpness statistic (dQ) against a +0.010 bar and
returned KEEP-OFF. That statistic is not obviously sensitive to the defect the
level-drift budget (facts 1633-1636) predicts: patchy per-region LEVEL offsets
in smooth background, which change tone, not sharpness.

So score the same two arms with a statistic shaped like the predicted defect.

  A0 = default merge            (gate 4)
  A1 = default merge + --photometric

Both were produced by M116 from a FROZEN warp map, so registration is held
constant and the only difference is the per-frame photometric fit.

Two statistics per window, because the predicted defect has energy at two
scales:
  hf   laplacian RMS          -- the boundaries BETWEEN level plateaus
  sdd  sd after a plane fit   -- the plateau level offsets themselves

Windows are selected from the SYMMETRIC MEAN of the two arms, so neither arm
can choose the pixels it is judged on (discipline 831 / fact 1630).

Commissioned in-run with three controls:
  NULL      A0 vs A0                      must be exactly 1.000
  PLANT+    A0+voronoi vs A0              must be >> 1  (can it see manufacture?)
  PLANT-    A0 vs A0+voronoi              must be << 1  (CAN IT SEE A REDUCTION?)
PLANT- is the one that matters: the claim under test is a reduction, and an
instrument that can only detect an increase cannot support it.

Reads only. Writes nothing outside C:\\dev\\strehl-out\\ORCH-morning.
"""
import os
import sys

import numpy as np
import tifffile

ROOT = r"C:\dev\strehl-out\M116\measure"
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]
BASE_ARM = "A0"
TEST_ARM = sys.argv[1] if len(sys.argv) > 1 else "A1"

S = 256
BORDER = 400
STRIDE = 128
NWIN = 12


def load(p):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit("%s read as %s, expected uint16 -- refusing" % (p, a.dtype))
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def hf(win):
    lap = (
        -4 * win[1:-1, 1:-1]
        + win[:-2, 1:-1]
        + win[2:, 1:-1]
        + win[1:-1, :-2]
        + win[1:-1, 2:]
    )
    return float(np.sqrt((lap ** 2).mean()))


_YY, _XX = np.mgrid[0:S, 0:S]
_B = np.stack([np.ones(S * S), _XX.ravel(), _YY.ravel()], axis=1)
_PINV = np.linalg.pinv(_B)


def sdd(win):
    """sd after removing a best-fit plane: plateau offsets, not the overall ramp."""
    f = win.ravel()
    return float((f - _B @ (_PINV @ f)).std())


def voronoi_plant(win, amp, seed=20260826):
    """Patchy per-region level offsets -- the shape the mechanism predicts."""
    rng = np.random.default_rng(seed)
    cx, cy = rng.integers(0, S, 40), rng.integers(0, S, 40)
    lab = ((_XX[..., None] - cx) ** 2 + (_YY[..., None] - cy) ** 2).argmin(axis=2)
    return win + rng.normal(0, amp, 40)[lab]


def windows(mean_img, singles_shape):
    H, W = singles_shape
    allw = []
    for y in range(BORDER, H - S - BORDER, STRIDE):
        for x in range(BORDER, W - S - BORDER, STRIDE):
            w = mean_img[y : y + S, x : x + S]
            allw.append((float(w.mean()), float(w[::8, ::8].std()), x, y))
    if not allw:
        raise SystemExit("no windows -- BORDER too large")
    bar = float(np.percentile([a[0] for a in allw], 80))
    pool = [a for a in allw if a[0] >= bar]
    pool.sort(key=lambda t: t[1])
    return [(t[2], t[3]) for t in pool[:NWIN]], bar, len(allw)


print("A/B: %s (base) vs %s (test); windows from the symmetric mean of the two"
      % (BASE_ARM, TEST_ARM))
print()

overall = []
for subj in SUBJECTS:
    p0 = os.path.join(ROOT, "%s__%s.tif" % (subj, BASE_ARM))
    p1 = os.path.join(ROOT, "%s__%s.tif" % (subj, TEST_ARM))
    if not (os.path.exists(p0) and os.path.exists(p1)):
        print("%s: MISSING arm file, skipping" % subj)
        continue
    A0 = load(p0)
    A1 = load(p1)
    if A0.shape != A1.shape:
        print("%s: GEOMETRY MISMATCH %s vs %s, skipping" % (subj, A0.shape, A1.shape))
        continue

    wins, bar, nscan = windows((A0 + A1) * 0.5, A0.shape)

    # ---- commissioning, on this subject's own pixels ----------------------
    w0 = A0[wins[0][1] : wins[0][1] + S, wins[0][0] : wins[0][0] + S]
    amp = max(sdd(w0), 1.0) * 2.0
    wp = voronoi_plant(w0, amp)
    c_null_hf = hf(w0) / hf(w0)
    c_up_hf = hf(wp) / hf(w0)
    c_dn_hf = hf(w0) / hf(wp)
    c_null_sd = sdd(w0) / sdd(w0)
    c_up_sd = sdd(wp) / sdd(w0)
    c_dn_sd = sdd(w0) / sdd(wp)
    ok = (
        abs(c_null_hf - 1.0) < 1e-12
        and abs(c_null_sd - 1.0) < 1e-12
        and c_up_hf > 1.3
        and c_dn_hf < 0.77
        and c_up_sd > 1.3
        and c_dn_sd < 0.77
    )
    print("=== %s ===  %d windows scanned, brightness bar %.0f" % (subj, nscan, bar))
    print("  commissioning (plant amp %.1f counts)" % amp)
    print("      null   hf %.4f  sdd %.4f   (want 1.0000)" % (c_null_hf, c_null_sd))
    print("      plant+ hf %.4f  sdd %.4f   (want >1.30)" % (c_up_hf, c_up_sd))
    print("      plant- hf %.4f  sdd %.4f   (want <0.77)  <-- the direction under test"
          % (c_dn_hf, c_dn_sd))
    if not ok:
        print("      INSTRUMENT FAILED COMMISSIONING on %s -- results not interpretable" % subj)
        continue
    print("      instrument OK")

    print("  %-6s %-6s %9s %9s %9s %9s %9s" % ("x", "y", "hf(A0)", "hf(test)", "hf ratio",
                                               "sdd rat", "lvl rat"))
    rh, rs = [], []
    for x, y in wins:
        a = A0[y : y + S, x : x + S]
        b = A1[y : y + S, x : x + S]
        h0, h1 = hf(a), hf(b)
        s0, s1 = sdd(a), sdd(b)
        rh.append(h1 / h0)
        rs.append(s1 / s0)
        print("  %-6d %-6d %9.1f %9.1f %9.4f %9.4f %9.5f"
              % (x, y, h0, h1, h1 / h0, s1 / s0, b.mean() / a.mean()))
    print("  MEDIAN  hf ratio %.4f   sdd ratio %.4f   (<1 = test arm manufactures less)"
          % (np.median(rh), np.median(rs)))
    print()
    overall.append((subj, float(np.median(rh)), float(np.median(rs))))

print("================ SUMMARY ================")
for subj, mh, ms in overall:
    verdict = "REDUCES" if (mh < 0.97 and ms < 0.97) else (
        "INCREASES" if (mh > 1.03 and ms > 1.03) else "no effect at this resolution")
    print("  %-14s hf %.4f  sdd %.4f   %s" % (subj, mh, ms, verdict))
if overall:
    print("  across subjects: median hf %.4f, median sdd %.4f"
          % (np.median([o[1] for o in overall]), np.median([o[2] for o in overall])))
