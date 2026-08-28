r"""Commission the ceiling-excess gauge FOR THIS USE before the ladder is run.

WHY A SECOND COMMISSIONING. This gauge was built for one comparison -- a master
against its own focus ceiling, once. It is about to be applied to a five-arm
ladder and asked to support a claim about the SHAPE of a trend. My own report
records what happens when a threshold or a statistic is carried across a change
of use without re-commissioning: MINSTEP, calibrated on tone-mapped data and
applied to linear light, selected zero sites and the harness printed a
conclusion from n = 0.

WHAT ORCH REQUIRED, AND WHY IT IS THE RIGHT BAR. Not "does the gauge report
something", but "does it report the RIGHT MAGNITUDE". A gauge that fires on any
disturbance whatsoever is a smoke alarm, and a ladder read on a smoke alarm
would show a trend wherever the arms differ at all -- which lad_probe.py already
measured at 98-99% of samples. Every arm would "respond" and the ladder would be
uninterpretable.

THE ARMS.

  SCALE   is the amplitude commissioning proper, and its prediction is EXACT
          rather than modelled. band() is std(DoG(a))/mean(a); DoG is linear and
          annihilates a constant, so for a' = mean(a) + k*(a - mean(a)) we have
          DoG(a') = k*DoG(a) and mean(a') = mean(a), hence band(a') = k*band(a)
          identically. Predicted excess is therefore k*(1+e0) - 1 with no fitted
          parameter and no independence assumption. k < 1 is A PLANTED
          IMPROVEMENT and k > 1 a planted defect, so the arm is two-sided by
          construction. This is the arm that would catch a statistic whose error
          sign is bounded below -- one that can ignore a defect but can never
          charge for an improvement. This project has shipped exactly that.

  INJECT  adds a bandpass-matched field INDEPENDENT of the image at five
          amplitudes. Independence is what licenses the quadrature prediction
          sqrt(band_a^2 + band_r^2), which is stated in advance from the base
          arm and the injected field alone -- never fitted to the result. The
          realised correlation is measured and printed, so the assumption is
          reported rather than asserted.

  HALO    is a physical unsharp overshoot: the shape manufactured detail
          actually takes. It is DIRECTIONAL AND MONOTONE ONLY, and is labelled
          as such, because the injected term is derived from the image and is
          therefore correlated with it, so no quadrature prediction is honest
          here. Reporting it as an exact-amplitude arm would be the same error
          as fitting a prediction to its own answer.

  BLUR    is the physical planted improvement: a Gaussian blur removes mid-band
          contrast, so a gauge that measures manufactured detail MUST read lower.

  NULL    is k = 1 / alpha = 0. It must reproduce the base value exactly, not
          approximately: the input is the same array.

  NANGUARD plants a NaN in the window. `NaN > x` is False, so an unguarded gauge
          reads an absent measurement as within-ceiling. A NaN reached cert.json
          in this same harness and would have read as a PASS.

EVERY MUTATION HARD-ERRORS IF IT DOES NOT LAND. A mutation that silently fails
to apply produces a green that means nothing -- the inert-plant failure, which
cost me two false greens on the certificate's own negative controls.

A DEFECT THIS ARM FOUND IN ITSELF, RECORDED BECAUSE IT IS THE ARGUMENT FOR THE
ARM. The first run failed SCALE at every k except 1.0, by 2e-3 to 9e-3 -- four
orders above float32 rounding on a relation claimed to be exact. lad_scalediag.py
isolated it: the relation is exact to 1.06e-07 in float32 and to 0.00e+00 in
float64, so the gauge was right and the HARNESS was wrong. The affine map was
built around the mean of the MARGINED window while band() normalises by the mean
of the CORE window, so the normaliser moved with k and the two disagreed by
exactly the 0.42% the two means differ by. Had the arm been written as "the
number should go up", it would have passed and the bug would have shipped inside
the instrument that certifies the ladder. SCALE and INJECT are pointwise or
additive and need no margin, so they now run on the core window directly and the
normaliser cannot move; only HALO and BLUR, which have spatial extent, take the
margin.
"""
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lad_measure as lm                                           # noqa: E402

SUB = "coffee-bubbles"
BASE = os.path.join(lm.LAD, "probe-default.tiff")
MARGIN = 32
WIN = lm.WIN
TOL_EXACT = 1e-4          # SCALE is analytic; only float32 rounding is allowed
TOL_MODEL = 0.05          # INJECT carries an independence assumption

fails = []


def check(name, ok, msg):
    print("  [%s] %-46s %s" % ("PASS" if ok else "FAIL", name, msg))
    if not ok:
        fails.append(name)


def must_change(before, after, what):
    """A plant that did not land must stop the run, never read as green."""
    if np.array_equal(before, after):
        raise SystemExit("MUTATION DID NOT LAND: %s left the array identical" % what)


def excess_of(win, ceiling):
    v = lm.band(win)
    if not lm.finite(v):
        return None
    return v / ceiling - 1.0


def main():
    sites, rec = lm.frozen_sites(SUB)
    if not sites:
        raise SystemExit("no frozen sites for %s -- cannot commission" % SUB)
    if not os.path.exists(BASE):
        raise SystemExit("base render missing: %s (run lad_probe.py first)" % BASE)
    ml, lat = lm.load_lum(BASE)
    print("commissioning on %s  lattice %s  %d frozen sites" % (SUB, lat, len(sites)))

    # One representative site, taken with a margin so that spatial mutations
    # (blur, halo) are not contaminated by the window boundary.
    s = sites[len(sites) // 2]
    y, x = s["y"], s["x"]
    big = np.array(ml[y - MARGIN:y + WIN + MARGIN, x - MARGIN:x + WIN + MARGIN],
                   dtype=np.float32)
    if big.shape != (WIN + 2 * MARGIN, WIN + 2 * MARGIN):
        raise SystemExit("site too close to the lattice edge to commission on")
    core = slice(MARGIN, MARGIN + WIN)
    # The window the gauge actually measures. SCALE/INJECT/NANGUARD mutate THIS,
    # so the normaliser band() divides by is the one the mutation was built on.
    base = np.array(big[core, core], dtype=np.float32)
    ceil = s["ceiling"]
    b0 = lm.band(base)
    e0 = b0 / ceil - 1.0
    print("  base band %.6f  ceiling %.6f  excess %+.4f%%\n" % (b0, ceil, 100 * e0))

    print("=== NULL: the same array must give the same number ===")
    again = excess_of(np.array(base), ceil)
    check("NULL", again == e0, "re-measured %+.6f%% vs %+.6f%%" % (100 * again, 100 * e0))

    print("\n=== SCALE: exact analytic amplitude, two-sided ===")
    print("  %-6s %14s %14s %12s" % ("k", "predicted", "measured", "rel err"))
    for k in (0.5, 0.8, 1.0, 1.25, 2.0):
        m = np.float32(base.mean())
        mut = (m + k * (base - m)).astype(np.float32)
        if k != 1.0:
            must_change(base, mut, "SCALE k=%s" % k)
        pred = k * (1.0 + e0) - 1.0
        got = excess_of(mut, ceil)
        rel = abs(got - pred) / max(abs(pred), 1e-9)
        print("  %-6s %13.6f%% %13.6f%% %11.2e" % (k, 100 * pred, 100 * got, rel))
        check("SCALE k=%s" % k, lm.finite(got) and rel < TOL_EXACT,
              "rel err %.2e < %.0e" % (rel, TOL_EXACT))
    # The improvement must actually be scored as one, not merely differ.
    mb = np.float32(base.mean())
    down = excess_of((mb + 0.5 * (base - mb)).astype(np.float32), ceil)
    up = excess_of((mb + 2.0 * (base - mb)).astype(np.float32), ceil)
    check("SCALE two-sided", lm.finite(down, up) and down < e0 < up,
          "improvement %+.3f%% < base %+.3f%% < defect %+.3f%%"
          % (100 * down, 100 * e0, 100 * up))

    print("\n=== INJECT: independent bandpass field, quadrature stated in advance ===")
    rng = np.random.default_rng(11)
    n = rng.standard_normal(base.shape).astype(np.float32)
    r0 = (ndimage.gaussian_filter(n, lm.SIG_LO)
          - ndimage.gaussian_filter(n, lm.SIG_HI)).astype(np.float32)
    r0 -= float(r0.mean())
    r0 /= float(r0.std())
    A0 = 0.25 * float(np.std(base))
    mean_base = float(np.mean(base))
    print("  %-6s %14s %14s %12s %10s" % ("alpha", "predicted", "measured", "rel err", "corr"))
    for a in (0.0, 0.25, 0.5, 1.0, 2.0):
        r = ((a * A0) * r0).astype(np.float32)
        mut = (base + r).astype(np.float32)
        if a != 0.0:
            must_change(base, mut, "INJECT alpha=%s" % a)
        # The injected field's own band contribution, normalised by the SAME
        # denominator the base sits on, so the two are addable in quadrature.
        br = float(np.std(ndimage.gaussian_filter(r, lm.SIG_LO)
                          - ndimage.gaussian_filter(r, lm.SIG_HI)) / mean_base)
        pred_band = float(np.hypot(b0, br))
        pred = pred_band / ceil - 1.0
        got = excess_of(mut, ceil)
        da = (ndimage.gaussian_filter(base, lm.SIG_LO)
              - ndimage.gaussian_filter(base, lm.SIG_HI))
        dr = (ndimage.gaussian_filter(r, lm.SIG_LO)
              - ndimage.gaussian_filter(r, lm.SIG_HI))
        corr = (float(np.mean((da - da.mean()) * (dr - dr.mean()))
                      / (da.std() * dr.std() + 1e-30)) if a > 0 else 0.0)
        rel = abs(got - pred) / max(abs(pred), 1e-9)
        print("  %-6s %13.6f%% %13.6f%% %11.2e %9.4f" % (a, 100 * pred, 100 * got, rel, corr))
        check("INJECT alpha=%s" % a, lm.finite(got) and rel < TOL_MODEL,
              "rel err %.2e < %.0e (corr %+.4f)" % (rel, TOL_MODEL, corr))

    print("\n=== HALO: physical unsharp overshoot -- directional and monotone only ===")
    prev, mono = e0, True
    for a in (0.10, 0.25, 0.50):
        mut = big + a * (big - ndimage.gaussian_filter(big, 2.0))
        must_change(big, mut, "HALO alpha=%s" % a)
        got = excess_of(mut[core, core], ceil)
        if not lm.finite(got) or got <= prev:
            mono = False
        print("  alpha %.2f -> excess %+.4f%%" % (a, 100 * got))
        prev = got
    check("HALO monotone up", mono, "a real overshoot raises the reading at every amplitude")

    print("\n=== BLUR: the physical planted IMPROVEMENT ===")
    prev, mono = e0, True
    for sg in (0.4, 0.8, 1.6):
        mut = ndimage.gaussian_filter(big, sg)
        must_change(big, mut, "BLUR sigma=%s" % sg)
        got = excess_of(mut[core, core], ceil)
        if not lm.finite(got) or got >= prev:
            mono = False
        print("  sigma %.1f -> excess %+.4f%%" % (sg, 100 * got))
        prev = got
    check("BLUR monotone down", mono,
          "removing mid-band contrast must LOWER manufactured-detail excess")

    print("\n=== NANGUARD: an absent measurement must not read as within-ceiling ===")
    mut = np.array(base)
    mut[10, 10] = np.nan
    must_change(np.nan_to_num(base, nan=-1), np.nan_to_num(mut, nan=-1), "NANGUARD")
    got = excess_of(mut, ceil)
    check("NANGUARD refuses", got is None, "gauge returned %r (None = refused)" % got)
    raw = float(np.std(ndimage.gaussian_filter(mut, lm.SIG_LO)
                       - ndimage.gaussian_filter(mut, lm.SIG_HI))
                / np.mean(mut))
    check("NANGUARD is load-bearing", not np.isfinite(raw) and not (raw > 0),
          "unguarded value is %r, and %r > 0 is %r -- would read as within-ceiling"
          % (raw, raw, raw > 0))

    print("\n%s  %d arm(s) failed: %s" % ("=" * 60, len(fails), fails or "none"))
    if fails:
        raise SystemExit(1)
    print("GAUGE COMMISSIONED for ladder use.")


if __name__ == "__main__":
    main()


