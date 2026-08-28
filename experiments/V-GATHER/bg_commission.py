r"""Commission the paired rim/rise gauge before it is allowed to judge anything.

WHAT ORCH ASKED THIS GAUGE TO DECIDE. Whether an arm that lowers rim did so by
removing the aura BESIDE the edge or by softening the edge ITSELF. A
step-normalised overshoot cannot answer that alone: blurring lowers it, and so
does a genuine fix.

THE DEFECT COMMISSIONING FOUND, AND WHY IT IS NOT TUNED AWAY. The obvious
companion statistic -- 10-90 rise on the same profile -- IS DRIVEN BY THE RIM.
A planted aura of 0.15 moved rise from 3.71 px to 3.18 px on an edge of
IDENTICAL blur, because elevating t=+2..+7 makes the profile reach 0.9 earlier.
A centre-slope variant (`rise_c`) reduced the coupling from -5.9 to -3.3 px per
unit rim but did not remove it, and carries a discretisation bias of +12% at
narrow edges. Neither is immune.

So the coupling is MEASURED AND USED rather than fought. It is the derivative of
rise with respect to rim at constant blur. Given an observed (d_rim, d_rise):

    d_rise_expected_from_dering = COUPLE * d_rim
    residual                    = d_rise - COUPLE * d_rim
    d_sigma_equivalent          = residual / K1090

`d_sigma_equivalent` is the change in edge blur in pixels of gaussian sigma,
with the aura's effect on the statistic already removed. A pure de-ringing must
read ~0. A pure blur must read the blur that was planted. Both are asserted
below AGAINST A PREDICTED VALUE on a real image, because a direction-only test
cannot see a broken fixture -- an earlier discriminator in this campaign read
0.9161 where 0.5000 was predicted, and only the value caught it.

The suite plants a DEGRADATION (blur, USM) and an IMPROVEMENT (a 1x5 median,
which removes a thin ridge and preserves a step by construction). A suite that
plants only degradations cannot distinguish a blind gauge from a perverse one.
"""
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter, gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bg_lib as L                                                 # noqa: E402

W, H = 1200, 900
SPACING = 60
K1090 = 2.0 * 1.2815515655446004
AMPS = (0.02, 0.05, 0.10, 0.15)


def synth(sigma_e, ring=0.0):
    x = np.arange(W)
    band = ((x // SPACING) % 2).astype(np.float64)
    img = gaussian_filter1d(0.2 + 0.6 * band, sigma_e)
    if ring:
        out = img.copy()
        for k in range(1, W // SPACING):
            cx = k * SPACING - 1
            if band[min(cx + 5, W - 1)] > band[max(cx - 5, 0)]:
                out[cx + 2:cx + 8] += ring * 0.6
            else:
                out[cx - 7:cx - 1] += ring * 0.6
        img = out
    return np.tile(img, (H, 1))


def check(name, got, pred, tol, unit=""):
    ok = bool(np.isfinite(got) and np.isfinite(pred) and abs(got - pred) <= tol)
    print("  %-40s got %8.4f%s pred %8.4f tol %.4f  %s"
          % (name, got, unit, pred, tol, "PASS" if ok else "**FAIL**"))
    return ok


def main():
    res = []
    print("=" * 84)
    print("A. rim and rise are CALIBRATED IN VALUE on synthetic edges")
    print("=" * 84)
    base = {}
    for se in (1.0, 1.5, 2.0):
        g = synth(se)
        m = L.measure(g, L.select(g, want=2000))
        eff = float(np.hypot(se, L.PRESMOOTH))
        base[se] = (m["rim"], m["rise"])
        print("\n clean step, blur sigma %.1f  (n=%d)" % (se, m["n"]))
        res.append(check("rim on a clean edge", m["rim"], 0.0, 0.005))
        res.append(check("rise = 2*1.2816*sqrt(s^2+1)", m["rise"], K1090 * eff,
                         0.05 * K1090 * eff, " px"))

    print("\n" + "=" * 84)
    print("B. rim measures AMPLITUDE, not presence -- a four-point ladder")
    print("=" * 84)
    clean = synth(1.0)
    sites = L.select(clean, want=2000)
    ctl = L.measure(clean, sites)
    keep = ctl["keep"]
    rise0 = ctl["rise"]
    xs, ys = [], []
    for amp in AMPS:
        m = L.measure(synth(1.0, ring=amp), sites, keep)
        res.append(check("planted %.2f -> rim" % amp, m["rim"], amp,
                         max(0.20 * amp, 0.006)))
        xs.append(m["rim"])
        ys.append(m["rise"] - rise0)
    print("\n   monotone in amplitude: %s"
          % ("PASS" if all(b > a for a, b in zip(xs, xs[1:])) else "**FAIL**"))
    res.append(all(b > a for a, b in zip(xs, xs[1:])))

    print("\n" + "=" * 84)
    print("C. the rise-vs-rim COUPLING, measured and fitted (not assumed zero)")
    print("=" * 84)
    A = np.vstack([np.asarray(xs), np.ones(len(xs))]).T
    slope, icept = np.linalg.lstsq(A, np.asarray(ys), rcond=None)[0]
    pred = A @ np.array([slope, icept])
    ss = 1.0 - np.sum((np.asarray(ys) - pred) ** 2) / max(
        np.sum((np.asarray(ys) - np.mean(ys)) ** 2), 1e-30)
    for a, b in zip(xs, ys):
        print("   rim %+.4f  ->  d_rise %+7.3f px" % (a, b))
    print("\n   COUPLE = %+.3f px per unit rim   (R^2 %.4f, intercept %+.4f)"
          % (slope, ss, icept))
    res.append(bool(ss > 0.95))
    print("   linear enough to correct with (R^2>0.95): %s"
          % ("PASS" if ss > 0.95 else "**FAIL**"))

    print("\n" + "=" * 84)
    print("D. REAL IMAGE -- the corrected statistic predicts a VALUE")
    print("=" * 84)
    a_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not a_path or not os.path.exists(a_path):
        print("  no image supplied; synthetic arms only")
        print("\n%d/%d arms PASS" % (sum(res), len(res)))
        np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "bg_couple.npy"), np.array([slope]))
        return 0 if all(res) else 1

    import tifffile
    g = L.luma(tifffile.imread(a_path))
    sites = L.select(gaussian_filter(g, 2.0))
    ctl = L.measure(g, sites)
    keepR = ctl["keep"]
    b_rim, b_rise = ctl["rim"], ctl["rise"]
    s0 = b_rise / K1090
    print("\n  base  rim %+.4f  rise %6.3f px  (sigma_eff %.3f)  n=%d of %d "
          "offered, from %d sites" % (b_rim, b_rise, s0, ctl["n"],
                                      ctl["offered"], len(sites)))

    SB = 1.2
    arms = {
        "BLUR sigma 1.2 (the trap)": (gaussian_filter(g, SB),
                                      K1090 * (np.hypot(s0, SB) - s0)),
        "MEDIAN 1x5 (improvement)": (median_filter(g, size=(1, 5)), 0.0),
        "USM (plants an aura)": (np.clip(g + 1.4 * (g - gaussian_filter(g, 1.2)),
                                         0, 1), None),
    }
    print("\n  %-26s %9s %9s %11s %11s" % ("arm", "d_rim", "d_rise",
                                           "resid px", "d_sigma_eq"))
    got = {}
    for nm, (arm, _) in arms.items():
        m = L.measure(arm, sites, keepR)
        d_rim, d_rise = m["rim"] - b_rim, m["rise"] - b_rise
        resid = d_rise - slope * d_rim
        got[nm] = (d_rim, d_rise, resid, resid / K1090)
        print("  %-26s %+9.4f %+9.3f %+11.3f %+11.3f   n=%d drop=%d"
              % (nm, d_rim, d_rise, resid, resid / K1090, m["n"], m["dropouts"]))

    print("\n  ACCEPTANCE -- values, not directions")
    nm = "BLUR sigma 1.2 (the trap)"
    pr = K1090 * (float(np.hypot(s0, SB)) - s0)
    res.append(check("BLUR: residual rise = predicted", got[nm][2], pr,
                     0.35 * pr, " px"))
    res.append(check("BLUR: d_sigma_eq recovers 1.2", got[nm][3],
                     float(np.hypot(s0, SB)) - s0, 0.35 * (float(np.hypot(s0, SB)) - s0),
                     " px"))
    res.append(check("BLUR lowers rim (it IS the trap)", 1.0 if got[nm][0] < 0 else 0.0,
                     1.0, 0.5))
    nm = "MEDIAN 1x5 (improvement)"
    res.append(check("MEDIAN: d_sigma_eq ~ 0 (no softening)", got[nm][3], 0.0,
                     0.15, " px"))
    res.append(check("MEDIAN lowers rim", 1.0 if got[nm][0] < 0 else 0.0, 1.0, 0.5))
    nm = "USM (plants an aura)"
    res.append(check("USM raises rim", 1.0 if got[nm][0] > 0.01 else 0.0, 1.0, 0.5))
    sep = got["BLUR sigma 1.2 (the trap)"][3] - got["MEDIAN 1x5 (improvement)"][3]
    res.append(check("blur and improvement SEPARATED in d_sigma_eq", sep,
                     float(np.hypot(s0, SB)) - s0, 0.5 * (float(np.hypot(s0, SB)) - s0),
                     " px"))

    np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "bg_couple.npy"), np.array([slope]))
    print("\n%d/%d arms PASS" % (sum(res), len(res)))
    return 0 if all(res) else 1


if __name__ == "__main__":
    sys.exit(main())