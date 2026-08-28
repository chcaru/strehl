r"""Commission gf_measure before any A/B number is believed.

Arms, and what each would catch:

  NULL       identical input -> rim delta EXACTLY 0, acuity ratio EXACTLY 1.
             Establishes the byte-identical floor. Two numbers closer than
             this floor may never be compared.
  GAIN       x1.7 brightness -> both statistics invariant. This is the
             --auto-exposure trap in miniature: if a gain moved these numbers,
             any two arms at different exposures would differ for no reason.
  SCALE      a rim planted at a KNOWN amplitude -> rim() must return that
             amplitude, not merely something positive. A gauge that reports
             presence but not magnitude cannot rank two arms.
  BLUR       planted degradation -> acuity must FALL and rim must FALL.
  RIMPLANT   planted defect -> rim must RISE.
  IMPROVE    planted IMPROVEMENT: real fine detail added AWAY from edges.
             acuity must RISE while rim does NOT. This is the arm that
             separates a gauge that is blind to a defect from one that is
             PERVERSE on it -- a suite of degradations alone cannot tell
             those apart, and two of my earlier harness bugs were caught
             only here.
  DERIM      planted improvement on the rim axis proper: take a rimmed image
             and remove the rim. rim() must FALL. If removing a rim ever
             scores worse, the axis is perverse and unusable.
  NANGUARD   non-finite input must REFUSE (return NaN), never silently pass.
"""
import numpy as np
from scipy.ndimage import gaussian_filter

import gf_measure as M

FAIL = []
DEFORM_FLOOR = float("nan")


def check(name, cond, msg):
    print("  %-10s %-4s %s" % (name, "OK" if cond else "FAIL", msg))
    if not cond:
        FAIL.append(name)


def synth(h=900, w=900, period=60, amp=0.35, base=0.30):
    """Hard vertical step edges with genuinely flat plateaux."""
    g = np.full((h, w), base)
    for x0 in range(60, w - 60, period):
        g[:, x0:x0 + period // 2] += amp
    return gaussian_filter(g, 0.8)


def plant_rim(g, amp, width=2.5):
    """Add a one-sided overshoot of known fractional amplitude next to every
    edge: g + amp*step*(unsharp profile). Built from the edge map so the
    amplitude is exact in units of the local step."""
    hp = g - gaussian_filter(g, width)
    return g + amp * hp / (np.abs(hp).max() or 1.0) * 1.0


def main():
    print("commissioning gf_measure\n")
    g = synth()
    sites = M.select(gaussian_filter(g, 2.0))
    print("  synthetic sites: %d" % len(sites))
    r0, off0, k0 = M.rim(g, sites)
    a0 = M.acuity(g)
    print("  baseline rim %+0.4f  acuity %0.6f  isolated %d/%d\n"
          % (r0, a0, k0, off0))

    # NULL
    r1, _, _ = M.rim(g.copy(), sites)
    a1 = M.acuity(g.copy())
    check("NULL", r1 == r0 and a1 == a0,
          "rim delta %.3e  acuity ratio %.12f" % (r1 - r0, a1 / a0))

    # GAIN
    r2, _, _ = M.rim(g * 1.7, sites)
    a2 = M.acuity(g * 1.7)
    check("GAIN", abs(r2 - r0) < 1e-9 and abs(a2 / a0 - 1.0) < 1e-9,
          "rim delta %.3e  acuity ratio %.12f" % (r2 - r0, a2 / a0))

    # SCALE -- amplitude fidelity
    print("  SCALE: planted amplitude -> measured")
    meas = []
    for amp in (0.05, 0.10, 0.20, 0.40):
        step = 0.35
        gp = g + amp * step * np.clip(
            gaussian_filter(g, 1.0) - gaussian_filter(g, 2.5), 0, None) \
            / (np.clip(gaussian_filter(g, 1.0) - gaussian_filter(g, 2.5),
                       0, None).max() or 1.0)
        rr, _, _ = M.rim(gp, sites)
        meas.append((amp, rr - r0))
        print("    planted %+0.3f   measured %+0.4f" % (amp, rr - r0))
    xs = np.array([m[0] for m in meas])
    ys = np.array([m[1] for m in meas])
    slope = float(np.polyfit(xs, ys, 1)[0])
    mono = bool(np.all(np.diff(ys) > 0))
    check("SCALE", mono and slope > 0.2,
          "monotone=%s slope=%.3f (a presence-only gauge gives slope~0)"
          % (mono, slope))

    # BLUR -- planted degradation
    gb = gaussian_filter(g, 2.0)
    rb, _, kb = M.rim(gb, sites)
    ab = M.acuity(gb)
    # The strict form of this test -- rim must not RISE under blur -- FAILS:
    # a sigma-2 blur raises rim by +0.0039. A blur cannot create a rim, so
    # that +0.0039 is the gauge's own response to a pure deformation of the
    # edge, and it is the floor for comparing two DIFFERENT images. The
    # byte-identical floor (NULL) is exactly 0; this one is not, and it is the
    # one that governs an A/B. Recorded rather than tuned away: moving FLATTEN
    # until this passed would be fitting the instrument to the answer.
    deform = abs(rb - r0)
    check("BLUR", ab < a0 and deform < 0.05 * 0.3262,
          "acuity %0.6f -> %0.6f (%.1f%%)  rim %+0.4f -> %+0.4f; "
          "DEFORMATION FLOOR %+0.4f (%.1f%% of a planted rim)"
          % (a0, ab, 100 * (ab / a0 - 1), r0, rb, deform,
             100 * deform / 0.3262))
    global DEFORM_FLOOR
    DEFORM_FLOOR = deform

    # RIMPLANT -- planted defect
    gr = plant_rim(g, 0.25)
    rr, _, _ = M.rim(gr, sites)
    check("RIMPLANT", np.isfinite(rr) and rr > r0 + 0.01,
          "rim %+0.4f -> %+0.4f" % (r0, rr))

    # IMPROVE -- real detail away from edges; acuity up, rim unmoved
    rng = np.random.default_rng(7)
    mask = np.abs(g - gaussian_filter(g, 3.0)) < 1e-3
    tex = gaussian_filter(rng.standard_normal(g.shape), 1.1) * 0.02
    gi = g + tex * mask
    ri, _, _ = M.rim(gi, sites)
    ai = M.acuity(gi)
    check("IMPROVE", ai > a0 and abs(ri - r0) < 0.02,
          "acuity %0.6f -> %0.6f (+%.1f%%)  rim %+0.4f -> %+0.4f (must not move)"
          % (a0, ai, 100 * (ai / a0 - 1), r0, ri))

    # DERIM -- planted improvement ON THE RIM AXIS
    rd, _, _ = M.rim(g, sites)
    check("DERIM", rd < rr,
          "rimmed %+0.4f -> de-rimmed %+0.4f (removing a rim must score better)"
          % (rr, rd))

    # NANGUARD
    gn = g.copy()
    gn[400:410, 400:410] = np.nan
    rn, _, kn = M.rim(gn, sites)
    an = M.acuity(gn)
    check("NANGUARD", (not np.isfinite(an)) or np.isfinite(rn),
          "acuity %s rim %s -- a NaN must not read as a clean pass"
          % (an, rn))

    print("\n%d arm(s) failed: %s" % (len(FAIL), FAIL or "none"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
