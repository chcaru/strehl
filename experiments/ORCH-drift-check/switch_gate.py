"""Score a candidate switch on BOTH axes, and let the control decide the verdict.

Tonight the soft gate beat the exposure-drift fix on every subject on the
background-cleanliness statistic, and it beat it because **it is a blur**. It
was caught by a texture check that lived in a different script and was read by
eye afterwards.

That is discipline 836 stated but not enforced: *any metric that rewards
removing something is maximised by removing everything, so it must be paired
with a region where removal is forbidden -- and that pairing must gate the
ranking, not annotate it.* `photometric_ab.py` selects the twelve SMOOTHEST
windows above a brightness bar and nothing else. It is structurally incapable of
seeing a blur. A candidate that erased the subject entirely would score
perfectly there.

So this script measures both axes on the same pixels, in one pass, and returns a
single verdict in which the control has a veto:

    REMOVAL      on the smoothest windows   -- want < 1 (manufactured structure gone)
    PRESERVATION on the most TEXTURED ones  -- want ~ 1 (real detail untouched)

    PASS  <=>  removal <= REMOVAL_BAR  AND  preservation >= PRESERVE_BAR

Windows for both pools are chosen from the SYMMETRIC MEAN of the two arms, so
neither arm can choose the pixels it is judged on (discipline 831 / fact 1630).

# Commissioning

Three controls, run on the subject's own pixels before any verdict is printed.
The third is the one this script exists for:

    NULL        base vs base            -- both axes exactly 1.000
    PLANT+      voronoi level patches   -- removal axis must respond
    PLANT-BLUR  base vs blurred base    -- **must be REJECTED**

`PLANT-BLUR` is a candidate that is nothing but a blur. If this instrument
passes it, the instrument cannot do the job it was written for and its verdicts
are worthless. An instrument that has never rejected a known-bad candidate is
not known to be able to reject one.

Usage:  python switch_gate.py [TEST_ARM]     (default A1)
Reads only. Writes nothing.
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
NWIN = 8

# Pre-registered bars. A candidate must clear BOTH.
REMOVAL_BAR = 0.97   # removal axis: at most this, i.e. a real reduction
PRESERVE_BAR = 0.97  # control axis: at least this, i.e. texture survives


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


def voronoi_plant(win, amp, seed=20260826):
    """Patchy per-region level offsets -- the shape the drift mechanism predicts."""
    rng = np.random.default_rng(seed)
    cx, cy = rng.integers(0, S, 40), rng.integers(0, S, 40)
    lab = ((_XX[..., None] - cx) ** 2 + (_YY[..., None] - cy) ** 2).argmin(axis=2)
    return win + rng.normal(0, amp, 40)[lab]


def _box1d(a, r, axis):
    n = a.shape[axis]
    pw = [(0, 0)] * a.ndim
    pw[axis] = (r, r)
    p = np.pad(a, pw, mode="reflect")
    c = np.cumsum(p, axis=axis)
    z = list(c.shape)
    z[axis] = 1
    c = np.concatenate([np.zeros(z), c], axis=axis)
    hi = [slice(None)] * a.ndim
    hi[axis] = slice(2 * r + 1, 2 * r + 1 + n)
    lo = [slice(None)] * a.ndim
    lo[axis] = slice(0, n)
    return (c[tuple(hi)] - c[tuple(lo)]) / (2 * r + 1)


def blur_plant(win, r=2):
    """A candidate that is purely a blur. The control MUST reject this."""
    return _box1d(_box1d(win, r, 0), r, 1)


def pools(mean_img, shape):
    """Smooth pool and textured pool, both from the symmetric mean."""
    H, W = shape
    allw = []
    for y in range(BORDER, H - S - BORDER, STRIDE):
        for x in range(BORDER, W - S - BORDER, STRIDE):
            w = mean_img[y : y + S, x : x + S]
            allw.append((float(w.mean()), float(w[::8, ::8].std()), x, y))
    if not allw:
        raise SystemExit("no windows -- BORDER too large")
    bar = float(np.percentile([a[0] for a in allw], 80))
    lit = [a for a in allw if a[0] >= bar]
    lit.sort(key=lambda t: t[1])
    smooth = [(t[2], t[3]) for t in lit[:NWIN]]
    # Texture pool is taken from ALL windows, not just the lit ones: subject
    # detail is not required to be in the brightest fifth of the frame.
    tex = sorted(allw, key=lambda t: -t[1])
    textured = [(t[2], t[3]) for t in tex[:NWIN]]
    return smooth, textured, bar, len(allw)


def med_ratio(A, B, wins):
    r = []
    for x, y in wins:
        a = A[y : y + S, x : x + S]
        b = B[y : y + S, x : x + S]
        h0 = hf(a)
        if h0 <= 0:
            continue
        r.append(hf(b) / h0)
    return float(np.median(r)) if r else float("nan")


def verdict(removal, preserve):
    if not (removal == removal and preserve == preserve):
        return "UNSCORABLE"
    if preserve < PRESERVE_BAR:
        return "REJECT (blurs: control %.4f < %.2f)" % (preserve, PRESERVE_BAR)
    if removal <= REMOVAL_BAR:
        return "PASS"
    return "no effect (removal %.4f > %.2f)" % (removal, REMOVAL_BAR)


print("switch gate: %s (base) vs %s (test)" % (BASE_ARM, TEST_ARM))
print("bars: removal <= %.2f AND preservation >= %.2f; the control has a veto"
      % (REMOVAL_BAR, PRESERVE_BAR))
print()

rows = []
for subj in SUBJECTS:
    p0 = os.path.join(ROOT, "%s__%s.tif" % (subj, BASE_ARM))
    p1 = os.path.join(ROOT, "%s__%s.tif" % (subj, TEST_ARM))
    if not (os.path.exists(p0) and os.path.exists(p1)):
        print("%s: MISSING arm file, skipping" % subj)
        continue
    A = load(p0)
    B = load(p1)
    if A.shape != B.shape:
        print("%s: GEOMETRY MISMATCH, skipping" % subj)
        continue

    smooth, textured, bar, n = pools((A + B) * 0.5, A.shape)
    print("=== %s ===  %d windows, brightness bar %.0f" % (subj, n, bar))

    # ---- commissioning ---------------------------------------------------
    ws = A[smooth[0][1] : smooth[0][1] + S, smooth[0][0] : smooth[0][0] + S]
    wt = A[textured[0][1] : textured[0][1] + S, textured[0][0] : textured[0][0] + S]
    amp = max(ws.std(), 1.0) * 2.0

    c_null_r = med_ratio(A, A, smooth)
    c_null_p = med_ratio(A, A, textured)
    c_up = hf(voronoi_plant(ws, amp)) / hf(ws)
    c_dn = hf(ws) / hf(voronoi_plant(ws, amp))
    # the blur candidate, scored the way a real candidate would be
    blur_rem = float(np.median([hf(blur_plant(A[y:y+S, x:x+S])) / hf(A[y:y+S, x:x+S])
                                for x, y in smooth]))
    blur_pre = float(np.median([hf(blur_plant(A[y:y+S, x:x+S])) / hf(A[y:y+S, x:x+S])
                                for x, y in textured]))
    blur_v = verdict(blur_rem, blur_pre)

    print("  commissioning")
    print("      null        removal %.4f  preserve %.4f   (want 1.0000 / 1.0000)"
          % (c_null_r, c_null_p))
    print("      plant+      hf %.4f   plant- hf %.4f      (want >1.30 / <0.77)"
          % (c_up, c_dn))
    print("      PLANT-BLUR  removal %.4f  preserve %.4f -> %s"
          % (blur_rem, blur_pre, blur_v))
    bad = []
    if abs(c_null_r - 1.0) > 1e-12 or abs(c_null_p - 1.0) > 1e-12:
        bad.append("null not unity")
    if not (c_up > 1.30 and c_dn < 0.77):
        bad.append("cannot see manufactured level patches")
    if not blur_v.startswith("REJECT"):
        bad.append("DID NOT REJECT A PURE BLUR -- this instrument cannot do its job")
    if bad:
        print("      INSTRUMENT FAILED COMMISSIONING: %s" % "; ".join(bad))
        print("      results on %s are not interpretable" % subj)
        print()
        continue
    print("      instrument OK (it rejected a blur, so its verdicts mean something)")

    removal = med_ratio(A, B, smooth)
    preserve = med_ratio(A, B, textured)
    v = verdict(removal, preserve)
    print("  removal      (smooth, n=%d)   %.4f" % (len(smooth), removal))
    print("  preservation (texture, n=%d)  %.4f   <-- the veto" % (len(textured), preserve))
    print("  VERDICT: %s" % v)
    print()
    rows.append((subj, removal, preserve, v))

print("================ SUMMARY: %s ================" % TEST_ARM)
for subj, r, p, v in rows:
    print("  %-14s removal %.4f  preserve %.4f   %s" % (subj, r, p, v))
if rows:
    # Aggregate last (discipline 835), and never let a good mean hide a veto.
    any_reject = any(v.startswith("REJECT") for _, _, _, v in rows)
    all_pass = all(v == "PASS" for _, _, _, v in rows)
    print()
    if any_reject:
        print("  OVERALL: REJECT -- blurs on at least one subject.")
        print("  A candidate that blurs anywhere is not rescued by scoring well elsewhere.")
    elif all_pass:
        print("  OVERALL: PASS on every subject.")
    else:
        print("  OVERALL: mixed; no subject shows harm, not every subject shows a win.")
sys.exit(0)
