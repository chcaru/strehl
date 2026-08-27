"""COHERENCE WITH THE HALF-STACK OFFSET REMOVED -- and a self-test that proves
the removal is real before any arm is measured.

WHAT WENT WRONG IN cohfree.py.  abshift.py measures the offset between each
arm's two half-stacks:

    strehl  113-A vs 113-B                    |d| median 1.319 px  (p90 1.776)
    enfuse  coh-enfuse-A vs -B                |d| median 0.029 px
    fs15    coh-fs15-A vs -B                  |d| median 0.039 px

A rigid offset d suppresses a cross-spectrum by cos(2*pi*f*d), which at the
pre-registered band midpoint f = 0.225 cyc/px is 0.156 for d = 1 px and 0.990
for d = 0.1 px.  So strehl's coherent power was being divided by roughly six for
a reason with nothing to do with resolution, and cohfree.py's
C_strehl / C_comp = 0.605 was measuring strehl's half-stack registration.

WHY THE ASYMMETRY EXISTS.  run_coh.ps1 gives each comparator ONE alignment pass
over all 63 frames and fuses subsets of it, so its halves share a raster by
construction.  strehl's halves came from running strehl separately on each
half-stack, so each chose its own alignment reference from its own frames.  That
is a property of how the halves were made, not of strehl as a stacker -- but it
handed the comparator an advantage, and in the direction that manufactures a
false retraction.  This was caught because strehl's coherent fraction at
0.05-0.10 cyc/px was 0.897 where enfuse's was 0.978, and at a period of 10-20 px
there is no photon noise left to be incoherent about.

THE CORRECTION.  Per ROI, measure the sub-pixel offset between the two halves,
then multiply one half's spectrum by exp(-2i*pi*(fy*dy + fx*dx)) before forming
the cross term.  This is exact: a pure phase ramp is a rigid translation, it
leaves |FA| and |FB| -- and therefore both arms' band POWERS -- untouched, and
it resamples nothing, so it cannot add or remove the blur being measured.  The
same treatment is applied to every arm.  On the comparators d is ~0.03 px so the
correction does essentially nothing, which is the control that shows the
correction is not what produces strehl's number.

THE SELF-TEST runs first and aborts on failure.  A real ROI is shifted by a
known non-integer amount in the Fourier domain and compared with itself.
Uncorrected, coherence must collapse in the fine bands; corrected, it must
return to ~1.000 in every band.  If the sign convention were wrong the corrected
figure would be worse than the uncorrected one and the test would fail loudly
rather than quietly reporting a flattering number.

STILL NOT REMOVED, unchanged from cohfree.py: noise common to both halves
(fixed-pattern, PRNU) is identical in every frame and survives on both arms;
deterministic sharpening or ringing is coherent by construction, so more
coherent fine structure means resolution OR overshoot.

INVOCATION (rule 47).  Reads:
    strehl      C:\\dev\\strehl-out\\V-H2H2\\lin\\113-{full,A,B}-g1.tiff
    comparator  C:\\dev\\strehl-out\\V-LINEAR2\\out\\coh-<tag>-{A,B}.tif
Writes nothing.  Prints only.

    python cohfix.py [nroi=48]
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2                                                        # noqa: E402
import rois                                                      # noqa: E402
from h2h2b import Comp, coarse, band_power, load, REF, PEAK_MIN, T, \
    PAD                                                          # noqa: E402
from h2free import FREE, BAND                                    # noqa: E402
from cohfree import ARMS, OUT, SCALE                             # noqa: E402
from abshift import subpixel_shift                               # noqa: E402

NAMES = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]
LO = np.array([b[0] for b in h2.BANDS])
HI = np.array([b[1] for b in h2.BANDS])

# THE SELF-TEST GATE, fixed before it was run against the arms.  The correction
# must recover at least this fraction of coherence at every band up to and
# including the pre-registered comparison band, for known offsets spanning the
# range actually observed (0.7-3.0 px, against strehl's measured 1.32 px).  It
# is not 1.000 and cannot be: h2.contrast_fft Hann-windows both crops, and a
# windowed shifted image is not a shifted windowed image, so a pure phase ramp
# is an approximation.  Bands above the comparison band are excluded from the
# gate because bandsignal.py already established they carry no signal on this
# corpus and no verdict is reported on them.
GATE = 0.97
bi = NAMES.index(BAND)


def ramp(t, dy, dx):
    fy = np.fft.fftfreq(t)[:, None]
    fx = np.fft.fftfreq(t)[None, :]
    return np.exp(-2j * np.pi * (fy * dy + fx * dx))


def cross(ca, cb, dy, dx, lo, hi):
    """Per-band Re(FA conj(FB)) with a rigid (dy,dx) removed from cb."""
    fa = h2.contrast_fft(ca)
    fb = h2.contrast_fft(cb)
    if fa is None or fb is None:
        return None
    t = ca.shape[0]
    fb = fb * ramp(t, dy, dx)
    norm = (t * t) ** 2 * (h2.window(t) ** 2).mean()
    cc = np.real(fa * np.conj(fb)) / norm
    r = h2.radial(t)
    return np.array([cc[(r >= a) & (r < b)].sum() for a, b in zip(lo, hi)])


class Arr:
    """Minimal croppable shim so the self-test can drive the SAME code path the
    real arms use, rather than a simplified version of it."""

    def __init__(self, a):
        self.g = a
        self.h, self.w = a.shape

    def crop(self, y0, x0, t):
        if y0 < 0 or x0 < 0 or y0 + t > self.h or x0 + t > self.w:
            return None, 1
        return self.g[y0:y0 + t, x0:x0 + t], 0


def pair_cross(A, B, y0, x0, t, lo, hi):
    """P(A), raw cross(A,B), and cross(A,B) with the half-stack offset removed.

    THE OFFSET IS REMOVED IN TWO STEPS, and the split matters.  The integer part
    is taken out by moving B's CROP WINDOW, which is exact and resamples
    nothing.  Only the sub-pixel remainder, now under half a pixel, is taken out
    by the phase ramp.  Doing the whole shift in the phase would be wrong: both
    crops are Hann-windowed by h2.contrast_fft, and a windowed shifted image is
    not a shifted windowed image, so the pure-ramp model degrades as the shift
    grows.  The self-test measures exactly that -- it passes at 0.6 px and fails
    at 1.15 px if the integer step is skipped -- and strehl's half-stacks are
    1.3 px apart, squarely in the failing regime.
    """
    ca, na = A.crop(y0, x0, t)
    cb0, nb = B.crop(y0, x0, t)
    if ca is None or cb0 is None or na or nb:
        return None
    dy, dx, good = refine_shift(ca, cb0)
    if not good:
        return None
    iy, ix = int(round(dy)), int(round(dx))
    cb, nb2 = B.crop(y0 - iy, x0 - ix, t)
    if cb is None or nb2:
        cb, iy, ix = cb0, 0, 0
    ry, rx, good = refine_shift(ca, cb)
    if not good:
        return None
    P = band_power(ca, lo, hi)
    Craw = cross(ca, cb0, 0.0, 0.0, lo, hi)
    Cfix = cross(ca, cb, ry, rx, lo, hi)
    if any(v is None for v in (P, Craw, Cfix)):
        return None
    return P, Craw, Cfix, float(np.hypot(dy, dx))


def refine_shift(ca, cb, iters=3):
    """Sub-pixel offset between two crops, by a weighted phase-slope fit.

    abshift.py's parabolic fit through the cross-correlation peak is good to
    only ~0.2 px on this data -- the self-test below catches that, which is why
    it exists -- and 0.2 px is still 0.28 rad at 0.225 cyc/px.  So the parabolic
    estimate is used ONLY as a starting point, and the residual is then read off
    the phase of the cross-spectrum, which is where the offset actually lives.

    The residual after the first step is well under half a pixel, so the phase
    ramp 2*pi*f*d cannot wrap inside the fitted disc (|f| < 0.30, |phase| <
    0.6 rad), and no unwrapping is needed.  Bins are weighted by |FA conj FB|,
    so the scene decides the fit and the noise-dominated bins do not -- the same
    reasoning h2.integer_shift gives for not whitening.
    """
    dy, dx, good = subpixel_shift(ca, cb)
    if not good:
        return dy, dx, False
    fa = h2.contrast_fft(ca)
    fb = h2.contrast_fft(cb)
    if fa is None or fb is None:
        return dy, dx, False
    t = ca.shape[0]
    r = h2.radial(t)
    m = (r > 0) & (r < 0.30)
    fy = np.fft.fftfreq(t)[:, None] * np.ones((1, t))
    fx = np.ones((t, 1)) * np.fft.fftfreq(t)[None, :]
    gy, gx = fy[m], fx[m]
    for _ in range(iters):
        x = (fa * np.conj(fb * ramp(t, dy, dx)))[m]
        w = np.abs(x)
        phi = np.angle(x)
        # phi ~= -2*pi*(gy*ey + gx*ex);  weighted least squares in (ey, ex)
        a = np.stack([-2 * np.pi * gy, -2 * np.pi * gx], 1)
        aw = a * w[:, None]
        try:
            sol, *_ = np.linalg.lstsq(aw, phi * w, rcond=None)
        except np.linalg.LinAlgError:
            return dy, dx, False
        dy += float(sol[0]); dx += float(sol[1])
    return dy, dx, True


def selftest(big):
    """Drives pair_cross exactly as the real arms do, on a synthetic pair whose
    offset is known, so a wrong sign or a degraded model fails loudly."""
    print("=" * 96)
    print("SELF-TEST: does the offset removal actually undo a known offset?")
    print("=" * 96)
    ok = True
    worst = []
    t = T
    pad = 8
    for (dy, dx) in ((0.37, -0.62), (-1.15, 0.44), (2.40, -1.73)):
        m = big.mean()
        moved = m + np.real(np.fft.ifft2(np.fft.fft2(big - m)
                                         * np.conj(ramp(big.shape[0], dy, dx))))
        A, B = Arr(big), Arr(moved)
        r = pair_cross(A, B, pad, pad, t, LO, HI)
        if r is None:
            print(f"  offset ({dy:+.2f},{dx:+.2f}): pair_cross returned None")
            return False
        P, Craw, Cfix, dmag = r
        raw, fix = Craw / P, Cfix / P
        print(f"\n  true offset ({dy:+.2f},{dx:+.2f}), |d| {np.hypot(dy, dx):.3f} px"
              f"   estimated |d| {dmag:.3f} px")
        print(f"    {'band':>11} {'uncorrected':>13} {'corrected':>11}")
        for i, nm in enumerate(NAMES):
            print(f"    {nm:>11} {raw[i]:13.4f} {fix[i]:11.4f}")
        bad = [NAMES[i] for i in range(bi + 1) if fix[i] < GATE]
        worst.append(min(fix[:bi + 1]))
        if bad:
            ok = False
            print(f"    FAIL: corrected coherence below {GATE} in {bad}")
        else:
            print(f"    PASS: corrected coherence >= {GATE} in every band up "
                  f"to and including {BAND}")
    if ok:
        print(f"\n  RESIDUAL BIAS.  The correction recovers "
              f"{100 * min(worst):.1f}% of coherence at worst, over offsets of "
              f"0.7-3.0 px\n  spanning the 1.32 px actually observed between "
              f"strehl's half-stacks.  The shortfall is a\n  Hann-window "
              f"effect: a windowed shifted image is not a shifted windowed "
              f"image, so a\n  pure phase ramp cannot be exact.  It runs "
              f"AGAINST the arm that needs the correction --\n  strehl, whose "
              f"halves are 1.32 px apart -- and NOT against the comparators, "
              f"whose halves\n  are 0.03 px apart and are therefore barely "
              f"corrected at all.  strehl's corrected C is\n  an "
              f"UNDERestimate by up to {100 * (1 - min(worst)):.1f}%.")
    return ok


def measure(A, B, S, det, F1, XF=None):
    """Per-ROI band powers and both raw and corrected cross-spectra."""
    TC = int(round(T / S))
    out = {k: [] for k in ("P", "Craw", "Cfix")}
    shifts = []
    used = drop = 0
    for (y, x) in det:
        c1, n1 = F1.crop(y, x, T)
        if n1:
            drop += 1
            continue
        y0 = int(round(y / S)); x0 = int(round(x / S))
        if XF is not None:
            cf, nc = XF.crop(y0, x0, TC)
            if cf is None or nc:
                drop += 1
                continue
            p, q = coarse(c1), coarse(cf)
            n = min(p.shape[0], q.shape[0])
            dy, dx, pk = h2.integer_shift(p[:n, :n], q[:n, :n], maxshift=6)
            if pk < PEAK_MIN:
                drop += 1
                continue
            y0 += dy * 4; x0 += dx * 4
        r = pair_cross(A, B, y0, x0, TC, LO * S, HI * S)
        if r is None:
            drop += 1
            continue
        P, Craw, Cfix, dmag = r
        out["P"].append(P); out["Craw"].append(Craw); out["Cfix"].append(Cfix)
        shifts.append(dmag)
        used += 1
    for k in out:
        out[k] = np.array(out[k])
    out["shift"] = np.array(shifts)
    out["used"] = used
    out["drop"] = drop
    return out


def main():
    nroi = int(sys.argv[1]) if len(sys.argv) > 1 else 48

    F1 = load("113-full-g1")
    detail, flat, counts = rois.census(F1, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(11)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]

    c0, _ = F1.crop(det[0][0], det[0][1], T + 16)
    if not selftest(c0):
        print("\nSELF-TEST FAILED -- the correction is not doing what it "
              "claims.\nNo arm is measured and no number is reported.")
        return 2

    print("\n" + "=" * 96)
    print(f"COHERENT vs COHERENT, half-stack offset removed.  band {BAND}")
    print("=" * 96)
    res = {}
    res["strehl"] = measure(load("113-A-g1"), load("113-B-g1"), 1.0, det, F1)
    for tag in ("enfuse", "fs15"):
        _, fa, fb, label = ARMS[tag]
        pa, pb = os.path.join(OUT, fa), os.path.join(OUT, fb)
        if not (os.path.exists(pa) and os.path.exists(pb)):
            continue
        W = FREE[tag]["weights"]
        full = os.path.join(OUT, ARMS[tag][0])
        res[tag] = measure(Comp(dict(path=pa, weights=W)),
                           Comp(dict(path=pb, weights=W)), SCALE[tag], det, F1,
                           XF=Comp(dict(path=full, weights=W)))
        res[tag]["label"] = label

    print(f"\n  {'arm':<10} {'n':>4} {'|d| med':>9}  coherent fraction C/P by band")
    print(f"  {'':<10} {'':>4} {'':>9}  " + " ".join(f"{n:>11}" for n in NAMES))
    for k, r in res.items():
        if r["used"] < 8:
            print(f"  {k:<10} only {r['used']} ROIs -- ABANDONED")
            continue
        cf = r["Cfix"].sum(0) / r["P"].sum(0)
        print(f"  {k:<10} {r['used']:>4} {np.median(r['shift']):9.3f}  "
              + " ".join(f"{v:11.3f}" for v in cf))
    print(f"\n  the same, WITHOUT the correction (what cohfree.py reported):")
    for k, r in res.items():
        if r["used"] < 8:
            continue
        cf = r["Craw"].sum(0) / r["P"].sum(0)
        print(f"  {k:<10} {r['used']:>4} {'':>9}  "
              + " ".join(f"{v:11.3f}" for v in cf))

    common = min(r["used"] for r in res.values())
    print(f"\n=== strehl / comparator, CORRECTED coherent power, 95% bootstrap "
          f"CI ===")
    print(f"  {'comparator':<38} {'band':>11} {'C_s/C_c':>9} {'CI95':>17}")
    verdicts = []
    for k, r in res.items():
        if k == "strehl" or r["used"] < 8:
            continue
        n = min(res["strehl"]["used"], r["used"])
        for i, nm in enumerate(NAMES):
            v, a, b = h2.bootstrap_ratio(res["strehl"]["Cfix"][:n, i],
                                         r["Cfix"][:n, i])
            mark = "  <==" if i == bi else ""
            print(f"  {(r['label'][:36] if i == bi else ''):<38} {nm:>11} "
                  f"{v:9.4f} [{a:6.3f},{b:6.3f}]{mark}")
        v, a, b = h2.bootstrap_ratio(res["strehl"]["Cfix"][:n, bi],
                                     r["Cfix"][:n, bi])
        verdicts.append((r["label"], v, a, b))
        print()

    print(f"=== VERDICT at {BAND}, coherent against coherent, offsets removed "
          f"===")
    for label, v, a, b in verdicts:
        if a > 1.05:
            w = "strehl AHEAD"
        elif b < 0.95:
            w = "strehl BEHIND"
        else:
            w = "LEVEL (CI spans the falsifier floor)"
        print(f"  vs {label[:52]:<52} C_s/C_c = {v:.3f} "
              f"[{a:.3f},{b:.3f}]  {w}")
    print(f"\n  floor: the NULL arm of gradeatsource.py has an identity bias of "
          f"0.8-1.7%\n  (0.9918 at {BAND}); a difference smaller than that is "
          f"not a difference.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
