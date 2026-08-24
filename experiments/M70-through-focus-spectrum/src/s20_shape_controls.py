"""M70 s20 - controls for a SCALE-FREE shape statistic.

The rescoped question (owner turn 3, M67 7.3 instruction (c)) is: are real
through-focus curves symmetric, and WHERE DOES THEIR SHAPE DEPART FROM A
GAUSSIAN?

Section 16.4 established that excess kurtosis g2 cannot answer this, because on a
plant that is symmetric BY CONSTRUCTION g2 runs -0.63 .. +6.13 purely as focus-
step density varies - it measures curve width relative to the moment window, not
shape. The fix is a statistic that is INVARIANT to curve width by construction:

    R(f1, f2) = w(f1) / w(f2)      ratio of half-widths at two fractions of peak

For a Gaussian exp(-x^2/2s^2), w(f) = s*sqrt(-2 ln f), so s cancels exactly:

    w25/w50 = sqrt(ln4  / ln2) = 1.414214
    w10/w50 = sqrt(ln10 / ln2) = 1.822615
    w10/w25 = sqrt(ln10 / ln4) = 1.288730

These are pure numbers with no free parameter. Heavier tails than Gaussian push
the ratio UP; a boxier curve pushes it DOWN. And because it is read at the 0.10
fraction it is a TAIL measurement, which is M67's instruction (c): fact 471's
FWHM agreement means any deviation lives in the tails, so a near-peak fit is
blind to it by construction. No parabola or Gaussian is fitted anywhere here.

Two tiers of control, because they answer different questions:
  ANALYTIC  - feed exact curves in, check the estimator returns the exact ratio.
  PHYSICAL  - feed a real-texture defocus ladder in, see what a genuine defocus
              curve gives, at blur-growth rates that BRACKET fact 471's measured
              real rates (0.6017 px/frame on 119MSDCF, 1.1856 on 109MSDCF).
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import m70lib as M  # noqa: E402
import s03_plant as P3  # noqa: E402
import s14_asym_controls as S14  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
SEED = 70

GAUSS = {
    "R25_50": math.sqrt(math.log(4.0) / math.log(2.0)),
    "R10_50": math.sqrt(math.log(10.0) / math.log(2.0)),
    "R10_25": math.sqrt(math.log(10.0) / math.log(4.0)),
}

# Fact 471, read from M67-focus-correctness.md line 520, NOT from a summary.
FACT471 = {"119MSDCF": 0.6017, "109MSDCF": 1.1856}


def widths(curve, smooth=True):
    o = {}
    for f in (0.50, 0.25, 0.10):
        wn, wf, cn, cf = S14.half_widths(curve, f, smooth=smooth)
        key = f"w{int(100 * f):02d}"
        o[key] = (wn + wf) / 2.0 if (np.isfinite(wn) and np.isfinite(wf)) else np.nan
        o[key + "_cens"] = bool(cn or cf)
    o["R25_50"] = o["w25"] / o["w50"] if o["w50"] else np.nan
    o["R10_50"] = o["w10"] / o["w50"] if o["w50"] else np.nan
    o["R10_25"] = o["w10"] / o["w25"] if o["w25"] else np.nan
    return o


def analytic(kind, K=201, scale=8.0):
    x = np.arange(K, dtype=np.float64) - (K - 1) / 2.0
    if kind == "gaussian":
        return np.exp(-0.5 * (x / scale) ** 2)
    if kind == "lorentzian":
        return 1.0 / (1.0 + (x / scale) ** 2)
    if kind == "triangle":
        return np.clip(1.0 - np.abs(x) / (3.0 * scale), 0.0, None)
    if kind == "boxcar":
        return (np.abs(x) <= 2.0 * scale).astype(np.float64)
    if kind == "sech2":
        return 1.0 / np.cosh(x / scale) ** 2
    raise ValueError(kind)


def hdr(t):
    print("\n" + "=" * 118)
    print(t)
    print("=" * 118)


def main() -> None:
    rng = np.random.default_rng(SEED)
    res = {"gauss_ideal": GAUSS, "fact471": FACT471}

    hdr("TIER 1 ANALYTIC - exact curves in, does the estimator return the exact ratio?")
    print("  Gaussian ideal:  R25/50 = %.6f   R10/50 = %.6f   R10/25 = %.6f"
          % (GAUSS["R25_50"], GAUSS["R10_50"], GAUSS["R10_25"]))
    print(f"\n{'curve':<14}{'w50':>9}{'w25':>9}{'w10':>9}"
          f"{'R25/50':>10}{'R10/50':>10}{'R10/25':>10}{'vs Gauss':>11}")
    res["analytic"] = {}
    for kind in ("gaussian", "sech2", "lorentzian", "triangle", "boxcar"):
        o = widths(analytic(kind), smooth=False)
        rel = o["R10_50"] / GAUSS["R10_50"]
        res["analytic"][kind] = {k: (None if not np.isfinite(v) else v)
                                 for k, v in o.items() if not k.endswith("_cens")}
        res["analytic"][kind]["rel_R10_50"] = float(rel)
        print(f"{kind:<14}{o['w50']:>9.3f}{o['w25']:>9.3f}{o['w10']:>9.3f}"
              f"{o['R25_50']:>10.4f}{o['R10_50']:>10.4f}{o['R10_25']:>10.4f}"
              f"{rel:>10.3f}x")
    ga = res["analytic"]["gaussian"]
    err = abs(ga["R10_50"] - GAUSS["R10_50"]) / GAUSS["R10_50"]
    print(f"\n  Estimator bias on an exact Gaussian: {100 * err:.3f}%  "
          f"({ga['R10_50']:.6f} vs {GAUSS['R10_50']:.6f})")
    print("  Lorentzian (heavy tails) reads HIGH, boxcar (no tails) reads LOW, as it must.")
    res["estimator_bias_pct"] = float(100 * err)

    hdr("TIER 1b - is the ratio SCALE-FREE? Same Gaussian, six different widths.")
    print(f"{'scale':>8}{'w50':>9}{'R10/50':>10}")
    sc = []
    for s in (2.0, 3.0, 5.0, 8.0, 13.0, 21.0):
        o = widths(analytic("gaussian", K=401, scale=s), smooth=False)
        sc.append(o["R10_50"])
        print(f"{s:>8.1f}{o['w50']:>9.3f}{o['R10_50']:>10.4f}")
    sc = np.array(sc)
    print(f"\n  spread over a 10.5x range of curve width: "
          f"{sc.max() / sc.min():.4f}x  (sd {sc.std(ddof=1):.4f})")
    print("  This is the property g2 lacked (section 16.4) and it is why the")
    print("  step-density confound cannot reach this statistic.")
    res["scale_free"] = {"ratios": sc.tolist(), "span": float(sc.max() / sc.min()),
                         "sd": float(sc.std(ddof=1))}

    hdr("TIER 2 PHYSICAL - a real-texture defocus ladder, at fact 471's MEASURED rates")
    print("  Fact 471 (M67 line 520, read at source): blur growth s = 0.6017 px/frame")
    print("  on 119MSDCF and 1.1856 on 109MSDCF. The sweep below BRACKETS both, so")
    print("  the plant is known to cover the real regime rather than assumed to.")
    print(f"\n{'delta px/step':>14}{'band':>9}{'w50':>9}{'w25':>9}{'w10':>9}"
          f"{'R10/50':>10}{'vs Gauss':>11}{'n':>5}")
    res["physical"] = []
    lat, _lat_mean = P3.load_latent()
    for d in (0.25, 0.50, 0.6017, 1.0, 1.1856, 2.0):
        acc = {"R10_50": [], "R25_50": [], "w50": []}
        for rep in range(12):
            r = np.abs(np.arange(41, dtype=np.float64) - 20.0) * d
            fr = P3.make_frames(lat, r, P3.LATENT_ISO,
                                np.random.default_rng(SEED + 1000 * rep + int(100 * d)))
            m = P3.measure_frames(fr, P3.LATENT_ISO, subtract_noise=True)
            for b in M.MID_BANDS:
                c = np.array([row[b] for row in m], dtype=np.float64)
                o = widths(c)
                for k in acc:
                    if np.isfinite(o[k]):
                        acc[k].append(o[k])
        if not acc["R10_50"]:
            print(f"{d:>14.4f}  (no finite curves - plant too narrow at this delta)")
            continue
        r10 = float(np.median(acc["R10_50"]))
        e = {"delta": d, "w50": float(np.median(acc["w50"])),
             "R25_50": float(np.median(acc["R25_50"])), "R10_50": r10,
             "rel": r10 / GAUSS["R10_50"], "n": len(acc["R10_50"])}
        res["physical"].append(e)
        print(f"{d:>14.4f}{'mid(3)':>9}{e['w50']:>9.3f}{'':>9}{'':>9}"
              f"{r10:>10.4f}{e['rel']:>10.3f}x{e['n']:>5}")

    hdr("TIER 3 NULL-NOISE - flat latent, calibrated noise, no curve at all")
    acc = []
    cens = 0
    for rep in range(48):
        fr = P3.make_frames(lat, np.zeros(41), P3.LATENT_ISO,
                            np.random.default_rng(SEED + 7000 + rep), noise=True)
        m = P3.measure_frames(fr, P3.LATENT_ISO, subtract_noise=True)
        for b in M.MID_BANDS:
            c = np.array([row[b] for row in m], dtype=np.float64)
            o = widths(c)
            if np.isfinite(o["R10_50"]):
                acc.append(o["R10_50"])
            else:
                cens += 1
    if acc:
        a = np.array(acc)
        print(f"  R10/50 median {np.median(a):.4f}  sd {a.std(ddof=1):.4f}  "
              f"n {a.size}  undefined {cens}")
        res["null_noise"] = {"median": float(np.median(a)), "sd": float(a.std(ddof=1)),
                             "n": int(a.size), "undefined": int(cens)}
    else:
        print(f"  no finite draws ({cens} undefined) - the statistic is undefined "
              f"where there is no curve, which is the correct behaviour")
        res["null_noise"] = {"median": None, "sd": None, "n": 0, "undefined": int(cens)}

    with open(os.path.join(OUT, "s20_shape_controls.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote out/s20_shape_controls.json")


if __name__ == "__main__":
    main()

