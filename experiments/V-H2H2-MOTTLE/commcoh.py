"""Commission the coherence instrument. It must be able to FAIL.

Arms are built so that each one can only pass for the reason it names. Two of
them exist because of failures other lanes hit tonight:

  - an identity control that returns exactly 1.0000 is worthless if it reached
    that value by a short-circuit rather than a computation (a lane's resamp.py
    returned a.copy() at s == 1). Here the identity arm is required to be exactly
    1 AND a perturbed copy is required to fall below it, so the value 1 is a
    prediction the arm could have failed.
  - a statistic that only ever sees degradations cannot be shown to be blind
    rather than perverse, so there is a planted IMPROVEMENT arm.

The arm that decides the whole question is 4: a pure translation must destroy
coherence at fine scales while leaving TOTAL band energy in one arm untouched.
If it does, then a coherence deficit is not evidence of a selection defect until
registration has been ruled out.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coh  # noqa: E402
import decomplib  # noqa: E402

RNG = np.random.default_rng(20260827)
N = 512
FAIL = []


def check(name, ok, detail):
    print("  %-4s %-46s %s" % ("PASS" if ok else "FAIL", name, detail))
    if not ok:
        FAIL.append(name)


def scene(n=N):
    """Broadband structure with real fine detail, not a smooth blob."""
    s = RNG.normal(0, 1, (n, n))
    out = np.zeros((n, n))
    for r, amp in ((1, 1.0), (3, 2.0), (8, 3.0), (24, 4.0)):
        out += amp * bandlib_blur(s, r)
    return 500.0 + 60.0 * out / out.std()


def bandlib_blur(x, r):
    import bandlib
    return bandlib.boxblur(x, r)


def shift(a, dy, dx):
    return np.roll(np.roll(a, dy, axis=0), dx, axis=1)


def mag(a, k):
    """Resample by 1+k about the centre. Used ONLY as a planted disturbance."""
    n = a.shape[0]
    c = (n - 1) / 2.0
    g = (np.arange(n) - c) / (1.0 + k) + c
    yy, xx = np.meshgrid(g, g, indexing="ij")
    y0 = np.clip(np.floor(yy).astype(int), 0, n - 2)
    x0 = np.clip(np.floor(xx).astype(int), 0, n - 2)
    fy, fx = yy - y0, xx - x0
    return ((1 - fy) * ((1 - fx) * a[y0, x0] + fx * a[y0, x0 + 1])
            + fy * ((1 - fx) * a[y0 + 1, x0] + fx * a[y0 + 1, x0 + 1]))


def band_noise(sd_target, lo, hi, n=N):
    """White noise whose energy IN THE MEASURED BAND is sd_target.

    Sizing a plant in raw sigma is how a commissioning arm ends up under-powered:
    bandpass(5,15) averages white noise down by more than an order of magnitude,
    so sigma 18 moved gamma by 1.4% and three arms passed that should not have.
    The plant is now sized in units of the quantity being measured.
    """
    z = RNG.normal(0, 1, (n, n))
    f = decomplib.bandpass(z, lo, hi)
    return z * (sd_target / max(float(f.std()), 1e-12))


def main():
    S = scene()
    LO, HI = 5, 15
    S_BAND = coh.total(S, LO, HI)
    nz = lambda r: band_noise(r * S_BAND, LO, HI)  # noqa: E731
    print("scene band energy at %d-%d px: %.4f; plants are sized as fractions of it\n"
          % (LO, HI, S_BAND))

    print("1. identity is a prediction, not a short-circuit")
    g = coh.gamma(S, S.copy(), LO, HI)
    gp = coh.gamma(S, S + nz(0.30), LO, HI)
    check("identical arms give exactly 1", g is not None and abs(g - 1.0) < 1e-12,
          "gamma = %.12f" % g)
    check("a perturbed copy gives less than 1", gp < g - 1e-3,
          "perturbed %.4f < identical %.12f" % (gp, g))

    print("\n2. independent noise is incoherent, and gamma matches the closed form")
    # fa = fs + fna, fb = fs + fnb with independent noise gives
    #   <fa fb> = <fs^2>,  <fa^2> = <fs^2> + <fn^2>
    # so gamma = 1 / (1 + r^2) exactly. This is an accuracy test against an
    # analytic value, not a direction test.
    ok, det = True, []
    for r in (0.10, 0.30, 0.90):
        v = coh.gamma(S + nz(r), S + nz(r), LO, HI)
        pred = 1.0 / (1.0 + r * r)
        det.append("r=%.2f %.4f vs %.4f" % (r, v, pred))
        ok = ok and abs(v - pred) < 0.02
    check("gamma equals 1/(1+r^2) at three noise levels", ok, "; ".join(det))

    print("\n3. selection incoherence is detected (the mechanism ORCH proposes)")
    # Each arm takes its band from a DIFFERENT random frame per pixel, which is
    # what noise-driven per-pixel selection does, with no displacement at all.
    # With the two arms agreeing on the frame at a fraction p of pixels,
    #   <fa fb> = <fs^2> + p <fn^2>,  <fa^2> = <fs^2> + <fn^2>
    # so gamma = (1 + p r^2) / (1 + r^2). A threshold guessed at 0.9 sat exactly
    # on this value at r = 0.5 and failed the arm by 0.0018; the closed form is
    # the honest bar.
    ok, det, gs = True, [], None
    for r in (0.50, 1.00):
        fa, fb = S + nz(r), S + nz(r)
        selA = np.where(RNG.random((N, N)) < 0.5, fa, fb)
        selB = np.where(RNG.random((N, N)) < 0.5, fa, fb)
        v = coh.gamma(selA, selB, LO, HI)
        pred = (1.0 + 0.5 * r * r) / (1.0 + r * r)
        det.append("r=%.2f %.4f vs %.4f" % (r, v, pred))
        ok = ok and abs(v - pred) < 0.02
        if r == 0.50:
            gs = v
    check("gamma equals (1+p r^2)/(1+r^2) under per-pixel selection", ok,
          "; ".join(det))

    print("\n4. THE DISCRIMINATOR: a pure shift destroys gamma but not total detail")
    rows = [(d, coh.gamma(S, shift(S, d, 0), LO, HI)) for d in (1, 3, 10)]
    t0 = coh.total(S, LO, HI)
    t10 = coh.total(shift(S, 10, 0), LO, HI)
    check("gamma falls monotonically with displacement",
          rows[0][1] > rows[1][1] > rows[2][1],
          "d=1 -> %.4f, d=3 -> %.4f, d=10 -> %.4f" % (rows[0][1], rows[1][1],
                                                      rows[2][1]))
    check("a 10 px shift destroys fine coherence", abs(rows[2][1]) < 0.2,
          "d=10 -> %.4f" % rows[2][1])
    check("total band energy is unmoved by the same shift",
          abs(t10 / t0 - 1.0) < 0.01,
          "total %.4f -> %.4f (%.2f%%)" % (t0, t10, 100 * (t10 / t0 - 1)))
    gc60 = coh.gamma(S, shift(S, 10, 0), 40, 120)
    check("the same shift costs far less at 40-120 px", gc60 > rows[2][1] + 0.3,
          "5-15 %.4f against 40-120 %.4f" % (rows[2][1], gc60))
    # A displacement and a selection defect are BOTH able to lower gamma, and the
    # instrument must be able to say so plainly: they are separated by whether
    # registration recovers it, which is arm 5, not by gamma alone.
    check("a shift and a selection defect are not distinguishable by gamma alone",
          abs(rows[1][1] - gs) < 0.5,
          "shift d=3 gives %.4f, selection gives %.4f -- registration decides, "
          "not the value" % (rows[1][1], gs))

    print("\n5. registration recovers a shift, and only partly recovers a scale")
    import nscene
    def reg_gamma(a, b, lo, hi):
        pad = np.pad(b, 64, mode="reflect")
        (dy, dx), _e, edge = nscene.integer_align(a, pad, 64)
        if edge:
            return None
        return coh.gamma(a, pad[64 + dy:64 + dy + N, 64 + dx:64 + dx + N], lo, hi)
    gr_sh = reg_gamma(S, shift(S, 7, -4), 5, 15)
    check("registration recovers a pure shift", gr_sh > 0.95,
          "raw %.4f -> registered %.4f" % (coh.gamma(S, shift(S, 7, -4), 5, 15), gr_sh))
    Smag = mag(S, 0.0067)
    g_raw = coh.gamma(S, Smag, 5, 15)
    g_reg = reg_gamma(S, Smag, 5, 15)
    check("an 0.67% scale is NOT fully recovered by an integer shift",
          g_reg is not None and g_reg < 0.95,
          "raw %.4f -> registered %.4f (the measured magnification is 0.67%%)"
          % (g_raw, g_reg))

    print("\n6. planted IMPROVEMENT: a sharper pair must not score worse")
    # A statistic that only ever sees degradations cannot be shown to be blind
    # rather than perverse. Both arms are sharpened coherently: total detail must
    # RISE and coherence must not collapse.
    def sharpen(a):
        import bandlib
        return a + 0.8 * (a - bandlib.boxblur(a, 2))
    A, B = S + nz(0.30), S + nz(0.30)
    tA, tAs = coh.total(A, 5, 15), coh.total(sharpen(A), 5, 15)
    gA, gAs = coh.gamma(A, B, 5, 15), coh.gamma(sharpen(A), sharpen(B), 5, 15)
    check("total detail rises on a genuinely sharper pair", tAs > tA * 1.1,
          "total %.4f -> %.4f (%+.1f%%)" % (tA, tAs, 100 * (tAs / tA - 1)))
    check("coherence is not destroyed by sharpening", gAs > gA - 0.15,
          "gamma %.4f -> %.4f" % (gA, gAs))

    print("\n7. gamma cannot be bought with a gain")
    check("a 40x gain on one arm leaves gamma unchanged",
          abs(coh.gamma(S, 40.0 * S, 5, 15) - 1.0) < 1e-9,
          "gamma = %.9f" % coh.gamma(S, 40.0 * S, 5, 15))

    print("\n8. HOSTILE: registration must not manufacture coherence")
    # This lane's conclusion is that registering the two halves recovers most of
    # the coherence deficit. That conclusion flatters us, so the arm that matters
    # is the one where it could be an artefact: aligning two images that share
    # NOTHING must not produce agreement. If the search can find a shift that
    # correlates pure noise, every recovery number in this section is worthless.
    a_n = band_noise(1.0, LO, HI)
    b_n = band_noise(1.0, LO, HI)
    g_raw_n = coh.gamma(a_n, b_n, LO, HI)
    # reg_gamma returns None here because the search saturates on pure noise --
    # it refuses. A refusal is the right behaviour but it is NOT the same as
    # "found nothing", and scoring it as a pass would be scoring a skip. So the
    # search is forced to hand back its best in-range shift and the coherence at
    # THAT shift is measured: the most favourable shift noise can offer.
    padn = np.pad(b_n, 64, mode="reflect")
    (dy, dx), _e, edge = nscene.integer_align(a_n, padn, 64)
    g_best_n = coh.gamma(a_n, padn[64 + dy:64 + dy + N, 64 + dx:64 + dx + N], LO, HI)
    check("the best shift found on pure noise still yields no coherence",
          abs(g_best_n) < 0.15,
          "raw %.4f -> best-shift %.4f at (%d,%d), search saturated=%s"
          % (g_raw_n, g_best_n, dy, dx, edge))
    # and where the pair IS noise-dominated but shares a scene, recovery must not
    # exceed what the shared scene justifies.
    g_reg_hn = reg_gamma(S + nz(3.0), S + nz(3.0), LO, HI)
    pred = 1.0 / (1.0 + 9.0)
    check("recovery on a noise-dominated pair stays near the closed form",
          g_reg_hn is not None and g_reg_hn < pred + 0.15,
          "registered %.4f against 1/(1+r^2) = %.4f at r = 3" % (g_reg_hn, pred))

    print("\n%s  (%d arm(s) failed)"
          % ("GREEN" if not FAIL else "RED: " + ", ".join(FAIL), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
