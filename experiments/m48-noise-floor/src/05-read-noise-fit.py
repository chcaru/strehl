"""M48 step 5 - the read-noise constants, and an attempt to kill the DN-floor
hypothesis (SYNTHESIS question 129).

Two jobs.

**Job 1 - what read_noise_e_high should be.** Under the shipped model
`sigma_DN^2 = g*S + (RN_e*g)^2` with `g = max(ISO, base_iso)/gain_divisor`, a
dark frame has `S = 0`, so `RN_e = sigma_DN / g` directly. This computes that at
all eleven measured ISOs on three estimator bases, and fits the single best
`RN_e` per gain mode under relative least squares (the objective that matters,
since sigma spans 6x across the table and an absolute-residual fit would be
dominated by ISO 2000).

**Job 2 - falsify the floor.** Question 129 proposes `sigma_DN^2 = a*ISO^2 + c`,
i.e. a gain-independent additive DN-domain term the shipped model omits. It was
formed from a two-point endpoint-anchored fit per mode, which is the weakest
evidence there is. Here it is fitted properly across all eleven ISOs at once and
attacked five ways:

  M0  f = 0, one RN_e per mode              2 params - what ships
  M1  one shared floor f, one RN_e per mode 3 params - question 129's claim
  M2  a floor per mode                      4 params - is the floor really shared?
  M3  sigma = k_mode * ISO_eff^p, shared p  3 params - the CONFOUND. A gain that
                                            is slightly sub-proportional to the
                                            marked ISO bends the curve the same
                                            way a floor does. Same parameter
                                            count as M1, so if M3 fits as well,
                                            the floor is not identified by dark
                                            frames and question 129 cannot be
                                            answered with this data.

  Attack 1: leave-one-ISO-out cross-validation. An extra parameter always
            improves the in-sample fit; only out-of-sample prediction is evidence.
  Attack 2: the physical floor. Any true gain-independent term must be at least
            14-bit quantisation, 1/sqrt(12) = 0.2887 DN. A fitted f below that is
            unphysical and the model is absorbing shape, not measuring a floor.
  Attack 3: per-plane consistency, which is the one test that separates M1 from
            M3 on physics. A post-gain additive DN floor is a property of the
            ADC and the digital path, so it must be THE SAME in all four CFA
            planes while `RN_e` differs (B reads ~9% below G2). A gain
            mis-specification is pre-gain, so it scales each plane's sigma
            proportionally and its fitted "floor" must scale as the plane's
            sigma, i.e. f_B/f_G2 ~ 0.91, not 1.00.
  Attack 4: both estimator bases. A floor that only exists on one basis is an
            estimator artifact.
  Attack 5: F-tests and AIC on 11 points, so the improvement is scored against
            the parameter it cost.

This changes no model. It reports.
"""

import json
import math
import os

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import f as f_dist

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

GAIN_DIVISOR = 436.8  # profile.rs
BASE_ISO = 100.0  # profile.rs, shipped 2a4f5c5
SECOND_BASE_ISO = 400.0  # profile.rs
QUANT_SD = 1.0 / math.sqrt(12.0)  # 14-bit quantisation, DN


def load():
    with open(os.path.join(DATA, "estimator-reconciliation.json")) as fh:
        rec = json.load(fh)
    with open(os.path.join(DATA, "variance-concentration.json")) as fh:
        conc = json.load(fh)["rows"]
    iso = np.array([r["iso"] for r in rec], float)
    bases = {
        "rms": np.array([r["n20"]["rms_sd"] for r in rec]),
        "mean": np.array([r["n20"]["mean_sd"] for r in rec]),
        "median": np.array([r["n20"]["median_sd"] for r in rec]),
    }
    planes = {
        p: np.array([next(c for c in conc if c["iso"] == i)["planes"][p]["rms_sd"] for i in iso])
        for p in ("R", "G1", "G2", "B")
    }
    return iso, bases, planes


def gain(iso):
    return np.maximum(iso, BASE_ISO) / GAIN_DIVISOR


def predict(params, iso, model):
    g = gain(iso)
    hi = iso >= SECOND_BASE_ISO
    if model == "M3":
        k_lo, k_hi, p = params
        k = np.where(hi, k_hi, k_lo)
        return k * np.maximum(iso, BASE_ISO) ** p
    rn = np.where(hi, params[1], params[0])
    if model == "M0":
        f = 0.0
    elif model == "M1":
        f = params[2]
    else:  # M2
        f = np.where(hi, params[3], params[2])
    return np.sqrt((rn * g) ** 2 + f**2)


P0 = {
    "M0": [4.0, 1.2],
    "M1": [4.0, 1.2, 0.4],
    "M2": [4.0, 1.2, 0.4, 0.4],
    "M3": [1e-2, 3e-3, 1.0],
}
NP = {"M0": 2, "M1": 3, "M2": 4, "M3": 3}


def fit(iso, obs, model):
    def resid(p):
        return predict(p, iso, model) / obs - 1.0

    lo = [0.0] * NP[model]
    hi = [np.inf] * NP[model]
    if model == "M3":
        lo, hi = [0.0, 0.0, 0.5], [np.inf, np.inf, 2.0]
    r = least_squares(resid, P0[model], bounds=(lo, hi), xtol=1e-15, ftol=1e-15)
    return r.x, r.fun


def aic(rss, n, k):
    return n * math.log(rss / n) + 2 * k


def ftest(rss0, k0, rss1, k1, n):
    """Nested F-test: is model 1 (k1 params) worth its extra parameters?"""
    if rss1 >= rss0 or k1 <= k0:
        return float("nan"), float("nan")
    fstat = ((rss0 - rss1) / (k1 - k0)) / (rss1 / (n - k1))
    return fstat, float(f_dist.sf(fstat, k1 - k0, n - k1))


def best_single_rn(iso, obs, mask):
    """RN_e minimising the RELATIVE residual on sigma over the masked ISOs."""
    rn_i = obs[mask] / gain(iso[mask])
    # d/dRN sum (RN/RN_i - 1)^2 = 0  ->  RN = sum(1/RN_i) / sum(1/RN_i^2)
    return float(np.sum(1 / rn_i) / np.sum(1 / rn_i**2)), rn_i


def main():
    iso, bases, planes = load()
    hi = iso >= SECOND_BASE_ISO
    lo = ~hi
    out = {}

    # ---------------- Job 1 ----------------
    print("=" * 78)
    print("JOB 1 - RN_e implied at every ISO, S = 0 so RN_e = sigma_DN / g")
    print("=" * 78)
    print(f"{'ISO':>5} {'g':>8} " + " ".join(f"{b:>9} {'RN_e':>8}" for b in bases))
    for j, i in enumerate(iso):
        row = f"{int(i):>5} {gain(i):8.5f} "
        row += " ".join(f"{bases[b][j]:9.4f} {bases[b][j] / gain(i):8.4f}" for b in bases)
        print(row)

    out["rn_fit"] = {}
    for b, obs in bases.items():
        print(f"\n--- basis '{b}': best single RN_e per mode, relative least squares ---")
        rec = {}
        for name, mask in (("low", lo), ("high", hi)):
            rn, rn_i = best_single_rn(iso, obs, mask)
            rel = rn / rn_i - 1
            rec[name] = dict(
                rn=rn,
                mean_rn=float(rn_i.mean()),
                max_abs_rel=float(np.max(np.abs(rel))),
                rms_rel=float(np.sqrt((rel**2).mean())),
                per_iso={int(i): float(r) for i, r in zip(iso[mask], rel)},
            )
            print(
                f"  {name:>4}: RN_e = {rn:.4f}  (unweighted mean {rn_i.mean():.4f})  "
                f"max |rel| {100 * np.max(np.abs(rel)):5.2f}%  rms rel {100 * np.sqrt((rel**2).mean()):5.2f}%"
            )
            print(
                "        per-ISO model/measured - 1: "
                + "  ".join(f"{int(i)}:{100 * r:+.2f}%" for i, r in zip(iso[mask], rel))
            )
        # what ships today
        for name, mask, shipped in (("low", lo, 4.20), ("high", hi, 1.47)):
            rn_i = obs[mask] / gain(iso[mask])
            rel = shipped / rn_i - 1
            print(
                f"  shipped {name} RN_e = {shipped}: "
                + "  ".join(f"{int(i)}:{100 * r:+.1f}%" for i, r in zip(iso[mask], rel))
            )
            rec[name]["shipped"] = shipped
            rec[name]["shipped_rel"] = {
                int(i): float(r) for i, r in zip(iso[mask], rel)
            }
        out["rn_fit"][b] = rec

    # ---------------- Job 2 ----------------
    print("\n" + "=" * 78)
    print("JOB 2 - the floor, fitted across ALL 11 ISOs at once")
    print("=" * 78)
    out["floor"] = {}
    for b in ("rms", "mean"):
        obs = bases[b]
        print(f"\n--- basis '{b}' ---")
        res = {}
        for m in ("M0", "M1", "M2", "M3"):
            p, r = fit(iso, obs, m)
            rss = float((r**2).sum())
            res[m] = dict(
                params=[float(x) for x in p],
                rss=rss,
                rms_rel=float(np.sqrt((r**2).mean())),
                max_abs_rel=float(np.max(np.abs(r))),
                aic=aic(rss, len(iso), NP[m]),
                resid={int(i): float(x) for i, x in zip(iso, r)},
            )
            pretty = {
                "M0": lambda p: f"RN_lo={p[0]:.4f} RN_hi={p[1]:.4f}",
                "M1": lambda p: f"RN_lo={p[0]:.4f} RN_hi={p[1]:.4f} floor={p[2]:.4f} DN",
                "M2": lambda p: f"RN_lo={p[0]:.4f} RN_hi={p[1]:.4f} f_lo={p[2]:.4f} f_hi={p[3]:.4f} DN",
                "M3": lambda p: f"k_lo={p[0]:.6g} k_hi={p[1]:.6g} exponent={p[2]:.4f}",
            }[m](p)
            print(
                f"  {m} ({NP[m]}p): {pretty}\n"
                f"        rms rel {100 * res[m]['rms_rel']:.3f}%  "
                f"max |rel| {100 * res[m]['max_abs_rel']:.3f}%  AIC {res[m]['aic']:.2f}"
            )
            print(
                "        residuals: "
                + " ".join(f"{int(i)}:{100 * x:+.2f}" for i, x in zip(iso, r))
            )
        n = len(iso)
        for a, c in (("M0", "M1"), ("M1", "M2"), ("M0", "M3")):
            fs, pv = ftest(res[a]["rss"], NP[a], res[c]["rss"], NP[c], n)
            print(f"  F-test {a} -> {c}: F = {fs:.3f}, p = {pv:.4g}")
            res[f"F_{a}_{c}"] = dict(F=fs, p=pv)
        print(
            f"  ATTACK 2 (physical floor): fitted shared floor {res['M1']['params'][2]:.4f} DN "
            f"vs 14-bit quantisation {QUANT_SD:.4f} DN -> "
            f"{'ABOVE, physical' if res['M1']['params'][2] > QUANT_SD else 'BELOW, UNPHYSICAL'}"
        )
        out["floor"][b] = res

    # Attack 1 - leave-one-ISO-out
    print("\n--- ATTACK 1: leave-one-ISO-out cross-validation (rms basis) ---")
    obs = bases["rms"]
    cv = {}
    for m in ("M0", "M1", "M2", "M3"):
        errs = []
        for j in range(len(iso)):
            keep = np.ones(len(iso), bool)
            keep[j] = False
            p, _ = fit(iso[keep], obs[keep], m)
            errs.append(float(predict(p, iso[j : j + 1], m)[0] / obs[j] - 1))
        cv[m] = dict(
            rms=float(np.sqrt(np.mean(np.square(errs)))),
            max_abs=float(np.max(np.abs(errs))),
            per_iso={int(i): e for i, e in zip(iso, errs)},
        )
        print(
            f"  {m}: held-out rms rel {100 * cv[m]['rms']:.3f}%  "
            f"max {100 * cv[m]['max_abs']:.3f}%   "
            + " ".join(f"{int(i)}:{100 * e:+.2f}" for i, e in zip(iso, errs))
        )
    out["loo_cv_rms_basis"] = cv

    # Attack 3 - per-plane floor consistency
    print("\n--- ATTACK 3: per-plane fit. Floor must be PLANE-INDEPENDENT if real ---")
    per_plane = {}
    for pname, obs in planes.items():
        p1, _ = fit(iso, obs, "M1")
        per_plane[pname] = dict(rn_lo=p1[0], rn_hi=p1[1], floor=p1[2])
        print(
            f"  {pname}: RN_lo={p1[0]:.4f} RN_hi={p1[1]:.4f} floor={p1[2]:.4f} DN  "
            f"(plane sigma at ISO 2000 = {obs[-1] if iso[-1] == 2000 else float('nan'):.4f})"
        )
    ref = per_plane["G2"]["floor"]
    sig2000 = {p: planes[p][list(iso).index(2000.0)] for p in planes}
    print("\n  prediction under each hypothesis, normalised to G2:")
    print(f"  {'plane':>6} {'floor/floor_G2':>15} {'sigma/sigma_G2':>15}  verdict axis")
    for p in ("R", "G1", "G2", "B"):
        print(
            f"  {p:>6} {per_plane[p]['floor'] / ref:15.4f} {sig2000[p] / sig2000['G2']:15.4f}"
        )
    print(
        "  A real post-gain DN floor predicts column 1 = 1.0000 for every plane.\n"
        "  A pre-gain (gain mis-specification) artifact predicts column 1 = column 2."
    )
    out["per_plane"] = {
        p: dict(per_plane[p], sigma2000_ratio_to_g2=sig2000[p] / sig2000["G2"])
        for p in per_plane
    }

    with open(os.path.join(DATA, "read-noise-fit.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"\nwrote {os.path.join(DATA, 'read-noise-fit.json')}")


if __name__ == "__main__":
    main()
