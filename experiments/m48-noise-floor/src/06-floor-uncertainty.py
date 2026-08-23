"""M48 step 6 - how well determined is the floor, and does the per-plane test
have any power?

Step 5 fitted the floor and ran three attacks on it. Two of them need error bars
before their verdict means anything:

  - the shared floor came out 0.5099 DN (rms basis) / 0.5411 DN (mean basis).
    Is that separated from the 14-bit quantisation floor 0.2887 DN by more than
    the fit's own uncertainty?
  - per-plane floors normalised to G2 came out R 1.016, G1 1.002, G2 1.000,
    B 0.882. A real post-gain floor predicts 1.000 everywhere; a pre-gain gain
    mis-specification predicts the plane's own sigma ratio (0.982, 0.987, 1.000,
    0.921). Three planes favour the floor and B favours neither. Whether that is
    evidence at all depends entirely on the uncertainty of a per-plane floor,
    which step 5 never computed. **AGENTS.md rule 20: an attack that cannot
    reject is arithmetic, not evidence.**

Two independent uncertainty estimates, because one is not checkable:

  - asymptotic, from the least-squares Jacobian;
  - delete-one-ISO jackknife over the eleven ISOs, which makes no normality
    assumption and is the right tool at n = 11.

No new measurement. This re-analyses `data/estimator-reconciliation.json` and
`data/variance-concentration.json`.
"""

import json
import math
import os

import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
QUANT_SD = 1.0 / math.sqrt(12.0)


def load():
    with open(os.path.join(DATA, "estimator-reconciliation.json")) as fh:
        rec = json.load(fh)
    with open(os.path.join(DATA, "variance-concentration.json")) as fh:
        conc = json.load(fh)["rows"]
    iso = np.array([r["iso"] for r in rec], float)
    series = {
        "rms": np.array([r["n20"]["rms_sd"] for r in rec]),
        "mean": np.array([r["n20"]["mean_sd"] for r in rec]),
    }
    for p in ("R", "G1", "G2", "B"):
        series[f"plane_{p}"] = np.array(
            [next(c for c in conc if c["iso"] == i)["planes"][p]["rms_sd"] for i in iso]
        )
    return iso, series


def m1_predict(p, iso):
    g = np.maximum(iso, BASE_ISO) / GAIN_DIVISOR
    rn = np.where(iso >= SECOND_BASE_ISO, p[1], p[0])
    return np.sqrt((rn * g) ** 2 + p[2] ** 2)


def m1_fit(iso, obs):
    r = least_squares(
        lambda p: m1_predict(p, iso) / obs - 1.0,
        [4.0, 1.2, 0.4],
        bounds=([0, 0, 0], [np.inf] * 3),
        xtol=1e-15,
        ftol=1e-15,
    )
    return r


def asymptotic_se(res, n, k):
    """Standard errors from the Jacobian of the relative-residual problem."""
    j = res.jac
    rss = float((res.fun**2).sum())
    s2 = rss / (n - k)
    cov = s2 * np.linalg.inv(j.T @ j)
    return np.sqrt(np.diag(cov))


def jackknife(iso, obs):
    """Delete-one-ISO jackknife over the eleven ISOs."""
    n = len(iso)
    full = m1_fit(iso, obs).x
    reps = []
    for j in range(n):
        keep = np.ones(n, bool)
        keep[j] = False
        reps.append(m1_fit(iso[keep], obs[keep]).x)
    reps = np.array(reps)
    mean = reps.mean(axis=0)
    se = np.sqrt((n - 1) / n * ((reps - mean) ** 2).sum(axis=0))
    return full, se, reps


def main():
    iso, series = load()
    out = {}
    print(f"{'series':>9} {'RN_lo':>18} {'RN_hi':>18} {'floor DN':>18}   n_sigma(floor vs quant)")
    for name, obs in series.items():
        res = m1_fit(iso, obs)
        se_a = asymptotic_se(res, len(iso), 3)
        full, se_j, _ = jackknife(iso, obs)
        se = np.maximum(se_a, se_j)  # report the more conservative of the two
        nsig = (full[2] - QUANT_SD) / se[2]
        out[name] = dict(
            params=[float(x) for x in full],
            se_asymptotic=[float(x) for x in se_a],
            se_jackknife=[float(x) for x in se_j],
            floor_n_sigma_above_quantisation=float(nsig),
        )
        print(
            f"{name:>9} "
            f"{full[0]:9.4f} +-{se[0]:6.4f} {full[1]:9.4f} +-{se[1]:6.4f} "
            f"{full[2]:9.4f} +-{se[2]:6.4f}   {nsig:6.1f}"
        )
    print(f"\n  (14-bit quantisation floor = {QUANT_SD:.4f} DN)")
    print("  se = max(asymptotic, delete-one-ISO jackknife), the more conservative")

    # ---- does the per-plane test have power? ----
    print("\n--- power of the per-plane floor test (ATTACK 3 of step 5) ---")
    g2 = out["plane_G2"]
    sig = {
        p: series[f"plane_{p}"][list(iso).index(2000.0)] for p in ("R", "G1", "G2", "B")
    }
    print(
        f"  {'plane':>6} {'floor/G2':>10} {'+-':>8} {'H_floor':>8} {'H_gain':>8} "
        f"{'z vs H_floor':>13} {'z vs H_gain':>12}"
    )
    power = {}
    for p in ("R", "G1", "B"):
        rec = out[f"plane_{p}"]
        f_p, f_g2 = rec["params"][2], g2["params"][2]
        se_p = max(rec["se_asymptotic"][2], rec["se_jackknife"][2])
        se_g2 = max(g2["se_asymptotic"][2], g2["se_jackknife"][2])
        ratio = f_p / f_g2
        # relative se of a ratio of two independent estimates
        rel = math.hypot(se_p / f_p, se_g2 / f_g2)
        se_ratio = ratio * rel
        h_gain = sig[p] / sig["G2"]
        z_floor = (ratio - 1.0) / se_ratio
        z_gain = (ratio - h_gain) / se_ratio
        power[p] = dict(
            ratio=ratio,
            se=se_ratio,
            h_gain=h_gain,
            z_vs_floor=z_floor,
            z_vs_gain=z_gain,
        )
        print(
            f"  {p:>6} {ratio:10.4f} {se_ratio:8.4f} {1.0:8.4f} {h_gain:8.4f} "
            f"{z_floor:13.2f} {z_gain:12.2f}"
        )
    sep = abs(1.0 - min(sig[p] / sig["G2"] for p in ("R", "G1", "B")))
    print(
        f"\n  The two hypotheses are at most {100 * sep:.1f}% apart (the B plane), and the\n"
        "  per-plane floor ratio carries the uncertainty above. A test can only\n"
        "  discriminate if that separation exceeds ~2x the ratio's standard error."
    )
    out["per_plane_power"] = power

    with open(os.path.join(DATA, "floor-uncertainty.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"\nwrote {os.path.join(DATA, 'floor-uncertainty.json')}")


if __name__ == "__main__":
    main()
