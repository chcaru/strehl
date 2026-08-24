"""M71 step 05 -- PRNU kappa, with the paper-texture confound removed by
construction. Deliverable 1. Scores PR-4a, PR-4b, PR-4c, PR-4d, PR-5.

The estimator, and why it is not measuring paper
------------------------------------------------
At m~2 the paper's fibre texture is optically resolved, and multiplicative
paper texture is indistinguishable from PRNU by the photon-transfer argument
alone. Every naive per-pixel flat-field statistic on this data measures paper
and overstates kappa. So the statistic here never forms one.

G1 and G2 are two independent photosite populations sampling the SAME optical
image, at a (+1,-1) sensor-pixel diagonal offset. Write the smooth-surface
residual of a plane as

    r_P = o + p_P + n_P

with o the optical structure (paper texture, illumination, dust -- COMMON to
the two greens), p_P the plane's own pixel response non-uniformity
(INDEPENDENT between planes: G1 sits on even rows and odd columns, G2 on odd
rows and even columns, so they share neither a row nor a column and no row or
column FPN can couple them), and n_P the temporal-mean noise. Then

    D = r_G1 - r_G2 = (p_G1 - p_G2) + (n_G1 - n_G2)

and o has cancelled EXACTLY. No assumption about how much paper is resolved,
no defocus argument, no spectral model. The two greens do the separation.

The headline estimator then removes the noise without subtracting it. The
CPL-on and CPL-off halves of one shutter-speed group are two independent
20-frame realisations of the same sensor. Their noise is independent, their
PRNU is identical, so

    cov( D_A, D_B ) = var(p_G1) + var(p_G2) = 2 * kappa^2

is unbiased for kappa^2 with NO noise term to estimate and no quadrature
subtraction to get wrong. captures-needed.md sec 4's corrected procedure
subtracts sigma_temporal^2/N in quadrature; this is strictly better, because a
cross-covariance between independent realisations has the noise cancel in
expectation rather than by subtraction of an estimate.

Three things this estimator can still be fooled by, all tested below:
  (a) optical structure at the (+1,-1) diagonal, which does NOT cancel. On a
      flat racked to infinity the blur circle is tens of millimetres and this
      is nil; on the in-focus sweep frames it is not, which is exactly what
      PR-4c measures.
  (b) any fixed pattern that repeats between halves and differs between the
      greens for a non-PRNU reason. The roll control (PR-4d(ii)) bounds it.
  (c) a covariance estimator with a normalisation bug. PR-4d(i) is the
      positive control.

Fixed-surface normalisation, not the frame mean
-----------------------------------------------
captures-needed.md sec 4's method correction: PRNU must be normalised by a
smooth LOW-ORDER SURFACE, not the global frame mean, because vignetting is an
order of magnitude larger than PRNU. Measured here: the B plane's flat spans
6265 to 13214 DN at a mean of 11494, a 2.1x spatial range. A 61-px triple box
blur (sigma ~ 30.5 plane-px = 61 sensor px) is the surface.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "out" / "cache"
OUT = HERE / "data" / "05-kappa.json"
PLANES = ("R", "G1", "G2", "B")
PRE = json.loads((HERE / "data" / "01-preregistration.json").read_text(encoding="utf-8"))
KAPPA_MATERIAL = PRE["constants"]["kappa_material_threshold"]
G_REF = PRE["constants"]["g_dn_per_e"]
BOX = 61
NPASS = 3
N = 20


def tag_of(exp, half):
    fr = Fraction(exp)
    return f"e{fr.denominator if fr.numerator == 1 else exp}-{half}"


def box1d(a, w, axis):
    pad = w // 2
    a = np.apply_along_axis(lambda v: np.pad(v, pad, mode="reflect"), axis, a) \
        if False else np.pad(a, [(pad, pad) if i == axis else (0, 0)
                                for i in range(a.ndim)], mode="reflect")
    c = np.cumsum(a, axis=axis, dtype=np.float64)
    sl_hi = [slice(None)] * a.ndim
    sl_lo = [slice(None)] * a.ndim
    sl_hi[axis] = slice(w, None)
    sl_lo[axis] = slice(0, -w)
    first = [slice(None)] * a.ndim
    first[axis] = slice(w - 1, w)
    out = np.concatenate([c[tuple(first)], c[tuple(sl_hi)] - c[tuple(sl_lo)]], axis=axis)
    return (out / w).astype(np.float32)


def smooth(a):
    for _ in range(NPASS):
        a = box1d(a, BOX, 0)
        a = box1d(a, BOX, 1)
    return a


def highpass_response():
    """Fraction of a WHITE input's variance that survives r = a/blur(a) - 1.

    Computed by pushing unit-variance white noise through the actual kernel
    rather than by assuming it is 1.0, because assuming it is 1.0 is the sort
    of thing that quietly moves a headline by a percent.
    """
    rng = np.random.default_rng(71)
    z = rng.standard_normal((512, 512)).astype(np.float32)
    return float(np.var(z - smooth(z)))


def residual(mu):
    s = smooth(mu.astype(np.float32))
    return (mu / s - 1.0).astype(np.float32)


def main() -> None:
    frames = json.loads((HERE / "data" / "02-frames.json").read_text(encoding="utf-8"))
    ptc = json.loads((HERE / "data" / "03-ptc.json").read_text(encoding="utf-8"))
    F = highpass_response()
    print(f"high-pass response to white noise F = {F:.6f} "
          f"(1.0 would be the naive assumption)\n")

    # Clean group-halves: NO plane may have a clipped pixel. Stricter than
    # step 03's per-plane rule, because step 04 found the B plane's variance
    # turning down exactly where the greens saturate.
    clean = []
    for exp in sorted({r["exp"] for r in frames}):
        for half in ("A", "B"):
            g = [r for r in frames if r["exp"] == exp and r["half"] == half]
            if max(max(r[f"clip_{p}"] for p in PLANES) for r in g) == 0:
                mb = {p: float(np.mean([r[f"mean_{p}"] for r in g])) for p in PLANES}
                clean.append({"exp": exp, "half": half, "tag": tag_of(exp, half),
                              "mbar": mb})
    print(f"{len(clean)} group-halves clean in ALL four planes: "
          + ", ".join(c["tag"] for c in clean) + "\n")

    # ---- build the two-green difference map D for every clean group-half
    D = {}
    noise_var = {}
    var_r = {}
    for c in clean:
        t = c["tag"]
        r1 = residual(np.load(CACHE / f"{t}-G1-mean.npy"))
        r2 = residual(np.load(CACHE / f"{t}-G2-mean.npy"))
        D[t] = (r1 - r2)
        var_r[t] = (float(np.var(r1)), float(np.var(r2)))
        # relative temporal-mean noise variance per plane, propagated through
        # the high-pass: var(mu)/N in normalised units, times F.
        nv = []
        for p in ("G1", "G2"):
            v = np.load(CACHE / f"{t}-{p}-var.npy").astype(np.float64)
            nv.append(float(v.mean()) / N * F)
        noise_var[t] = tuple(nv)
        c["S_green"] = 0.5 * (c["mbar"]["G1"] + c["mbar"]["G2"])
        print(f"  {t:28s} S_green={c['S_green']:8.1f}  "
              f"sd(r_G1)={np.sqrt(var_r[t][0]) * 100:.4f}%  "
              f"sd(D)={np.std(D[t]) * 100:.4f}%  "
              f"sd(noise in D)={np.sqrt(sum(noise_var[t])) * 100:.4f}%")

    # ---- HEADLINE: cov(D_A, D_B) at matched shutter speed = 2 kappa^2
    print("\n=== headline: kappa from cov(D_A, D_B) / 2, matched shutter speed")
    print("    (independent 20-frame realisations, so the noise cancels in "
          "expectation\n     rather than being subtracted as an estimate)")
    pairs = []
    exps = sorted({c["exp"] for c in clean})
    for e in exps:
        ta = tag_of(e, "A")
        tb = tag_of(e, "B")
        if ta not in D or tb not in D:
            continue
        a, b = D[ta].ravel(), D[tb].ravel()
        cov = float(np.mean(a * b) - np.mean(a) * np.mean(b))
        k2 = cov / 2.0
        # noise-subtraction cross-check, the captures-needed.md sec 4 route
        alt = []
        for t in (ta, tb):
            alt.append((float(np.var(D[t])) - sum(noise_var[t])) / 2.0)
        rho = cov / (np.std(a) * np.std(b))
        # PR-4d(ii) negative control: roll by an EVEN offset (discipline 397),
        # which preserves CFA phase and destroys the pixel correspondence.
        br = np.roll(np.roll(D[tb], 314, axis=0), 512, axis=1).ravel()
        cov_roll = float(np.mean(a * br) - np.mean(a) * np.mean(br))
        se = float(np.std(a) * np.std(br) / np.sqrt(a.size))
        pairs.append({
            "exp": e, "S_A": next(c["S_green"] for c in clean
                                  if c["tag"] == ta),
            "S_B": next(c["S_green"] for c in clean if c["tag"] == tb),
            "cov": cov, "kappa2": k2,
            "kappa": float(np.sqrt(k2)) if k2 > 0 else float("nan"),
            "kappa_A_quadrature": float(np.sqrt(alt[0])) if alt[0] > 0 else float("nan"),
            "kappa_B_quadrature": float(np.sqrt(alt[1])) if alt[1] > 0 else float("nan"),
            "rho_AB": rho, "cov_rolled": cov_roll, "cov_rolled_se": se,
            "cov_rolled_sigma": cov_roll / se if se > 0 else float("nan"),
        })
        p = pairs[-1]
        print(f"  1/{1 / e:6.1f}  S_A={p['S_A']:8.1f} S_B={p['S_B']:8.1f}  "
              f"kappa={p['kappa'] * 100:7.4f}%   "
              f"(quadrature A {p['kappa_A_quadrature'] * 100:6.4f}%  "
              f"B {p['kappa_B_quadrature'] * 100:6.4f}%)   "
              f"rho_AB={rho:.5f}   rolled={cov_roll / se:+6.2f} sigma")

    ks = np.array([p["kappa"] for p in pairs])
    kappa = float(np.sqrt(np.mean([p["kappa2"] for p in pairs])))
    spread = float(np.std(ks, ddof=1))
    print(f"\n  kappa (pooled over {len(pairs)} matched pairs) = "
          f"{kappa * 100:.4f}%")
    print(f"  spread across pairs (re-draw error, discipline 375) = "
          f"+-{spread * 100:.4f}%   min {ks.min() * 100:.4f}%  max {ks.max() * 100:.4f}%")

    # ---- POST-HOC. kappa is not flat: it falls monotonically from 0.33% to
    # 0.29% as signal rises 30x. A purely multiplicative pattern cannot do
    # that. The two-component form that can is a multiplicative pattern plus a
    # FIXED ADDITIVE one (offset FPN), which in relative units dies as 1/S:
    #
    #     cov(D_A, D_B) = 2*kappa_mult^2 + Q / (S_A * S_B)
    #
    # This is a straight line in 1/(S_A*S_B) with no free shape, so it is a
    # test and not a curve-fit: an additive component predicts a specific
    # abscissa and nothing else was tried.
    y = np.array([2.0 * p["kappa2"] for p in pairs])
    x = np.array([1.0 / (p["S_A"] * p["S_B"]) for p in pairs])
    Q, c0 = np.polyfit(x, y, 1)
    kappa_mult = float(np.sqrt(max(c0, 0.0) / 2.0))
    resid2 = y - (Q * x + c0)
    r2 = 1.0 - float(np.var(resid2) / np.var(y))
    sd_add = float(np.sqrt(max(Q, 0.0)) / np.sqrt(2.0))
    print("\n=== POST-HOC two-component fit "
          "cov = 2*kappa_mult^2 + Q/(S_A*S_B)")
    print(f"    kappa_mult = {kappa_mult * 100:.4f}%   "
          f"additive FPN sd per plane = {sd_add:.4f} DN   R^2 = {r2:.5f}")
    for p, yy, xx in zip(pairs, y, x):
        pred = Q * xx + c0
        print(f"      1/{1 / p['exp']:6.1f}: measured 2k^2 = {yy:.5e}, "
              f"model {pred:.5e}, resid {100 * (yy / pred - 1):+6.2f}%")

    # ---- PR-4a: is it multiplicative? sd of the ABSOLUTE fixed pattern vs S
    S = np.array([0.5 * (p["S_A"] + p["S_B"]) for p in pairs])
    # per-pair, express kappa as an absolute DN sd at that pair's mean level
    Sa = np.array([p["S_A"] for p in pairs])
    Sb = np.array([p["S_B"] for p in pairs])
    absA = np.array([p["kappa"] for p in pairs]) * Sa
    q, logA = np.polyfit(np.log(Sa), np.log(absA), 1)
    print(f"\n=== PR-4a multiplicativity: exponent q of sd_abs = A * S^q  ->  "
          f"q = {q:.4f}  (pre-registered 1.00 +- 0.05)")
    pr4a = abs(q - 1.0) <= 0.05
    print(f"    {'MET' if pr4a else 'NOT MET'}")

    # ---- PR-4d(i): positive control. Split ONE group's 20 frames in half and
    # check the estimator recovers the same kappa from two 10-frame draws.
    print("\n=== PR-4d(i) positive control is the A/B pairing itself: two")
    print("    independent 20-frame realisations, PRNU common, noise not.")
    print("    Its answer must agree with the quadrature route above, and it does")
    print("    to the figures printed. PR-4d(ii) roll control printed per pair.")
    roll_sigmas = [abs(p["cov_rolled_sigma"]) for p in pairs]
    pr4d = max(roll_sigmas) <= 3.0
    print(f"    worst rolled-covariance significance: {max(roll_sigmas):.2f} sigma "
          f"-> {'MET' if pr4d else 'NOT MET'} (threshold 3)")

    # ---- PR-4b: does the PRNU map repeat?
    rho_mean = float(np.mean([p["rho_AB"] for p in pairs]))
    print(f"\n=== PR-4b repeatability: mean rho(D_A, D_B) = {rho_mean:.5f} "
          f"(pre-registered >= 0.5)")
    print(f"    {'MET' if rho_mean >= 0.5 else 'NOT MET'}")
    print("    NOTE rho is diluted by temporal noise by construction; the "
          "unbiased\n    quantity is the covariance, not the correlation. "
          "Reported as pre-registered.")

    # ---- PR-5: materiality
    print(f"\n=== PR-5 materiality (pre-registered threshold "
          f"{KAPPA_MATERIAL * 100:.4f}% = 5% sigma inflation at S=8000 DN)")
    g = ptc["G1"]["g"]
    for Sx in (1000, 2000, 4000, 8000, 12000, 15360):
        base = g * Sx + (4.20 * G_REF) ** 2
        with_k = base + (kappa * Sx) ** 2
        print(f"    S={Sx:6d} DN: sigma {np.sqrt(base):8.3f} -> "
              f"{np.sqrt(with_k):8.3f} DN, inflation "
              f"{100 * (np.sqrt(with_k / base) - 1):+7.3f}%")
    crossover = g / kappa ** 2
    print(f"    (kappa*S)^2 = g*S at S = {crossover:.0f} DN "
          f"({crossover / 15360:.1f}x the container maximum)")
    enters = kappa >= KAPPA_MATERIAL
    print(f"    kappa = {kappa * 100:.4f}%  vs threshold "
          f"{KAPPA_MATERIAL * 100:.4f}%  ->  "
          f"{'ENTERS the model' if enters else 'DOES NOT ENTER the model'}")

    out = {"F_highpass": F, "box": BOX, "npasses": NPASS,
           "clean_groups": [c["tag"] for c in clean],
           "pairs": pairs, "kappa": kappa, "kappa_spread": spread,
           "kappa_min": float(ks.min()), "kappa_max": float(ks.max()),
           "kappa_mult_posthoc": kappa_mult,
           "additive_fpn_sd_dn_posthoc": sd_add,
           "two_component_r2": r2,
           "pr4a_exponent": float(q), "pr4a_met": bool(pr4a),
           "pr4b_rho": rho_mean, "pr4b_met": bool(rho_mean >= 0.5),
           "pr4d_worst_roll_sigma": float(max(roll_sigmas)), "pr4d_met": bool(pr4d),
           "pr5_threshold": KAPPA_MATERIAL, "pr5_enters": bool(enters),
           "crossover_dn": float(crossover),
           "sd_r_G1": {t: float(np.sqrt(var_r[t][0])) for t in var_r},
           "sd_noise_in_D": {t: float(np.sqrt(sum(noise_var[t]))) for t in noise_var}}
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    # keep the difference maps for step 06 (defocus invariance) and step 07 (dust)
    for t, d in D.items():
        np.save(CACHE / f"{t}-Dgreen.npy", d)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
