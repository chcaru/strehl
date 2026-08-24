"""M69 arm A7 -- the second observation, and a control that can fail.

M69 was told, after dispatch, that M62 "reproduced the effect independently on
its own plant at its own seeds -- rho = 1.2124 at seeds 0 and 1", and that a
refutation must therefore explain two independent observations.

Reading the sources rather than the summary (see the report, section 3b):
rho = 1.2124 / 1.2122 is M66's OWN fact 9, arm B, and M62's addendum says in
terms "No re-run ... I implemented nothing." So there is one observation, made
twice by one milestone with two estimators on one plant. This arm reproduces the
SECOND estimator -- the temporal one at N = 299 -- which M69 had not yet run, so
that both of M66's numbers are accounted for rather than only the spatial one.

The control that can fail
-------------------------
M69's explanation of both numbers is the FROZEN-LATENT defect: a real frame is
T + eta, and M66's replicates are T + eta_0 + epsilon, so the plant's latent
carries E|grad eta|^2 = 2 s^2 of gradient energy that a real frame's latent does
not. That is an algebraic claim, and so far it has only been checked against P2.

Here it is made to make a PREDICTION THAT CAN FAIL. Freeze k independent noise
realisations into the latent instead of one:

    L_k = L + sum_{i=2..k} eta_i        (M66's plant is k = 1)

Each added realisation adds exactly the same 2 s^2 of spurious gradient the
freeze already added, so k indexes the defect in known units. Measure rho(L_k)
for k = 1, 2, 3 and predict all three with P2 -- which was validated against a
completely different family (the A3 synthetic sweep) and knows nothing of this
construction.

  * If the mechanism is right, rho rises with k, P2 tracks it, and the
    back-extrapolation to k = 0 -- the defect-free plant, which cannot be built
    from one real frame -- is the corrected number.
  * If rho is flat in k, or moves the other way, or P2 misses the STEP by more
    than the step itself, the frozen-latent explanation is WRONG and M69's
    account of 1.1921 and 1.2124 collapses. That is a real failure mode and it
    is the point of running it.

Bar, fixed here before the run: P2 must predict each measured rho(L_k) to within
5% ABSOLUTE, and must predict the k=1 -> k=3 STEP to within 30% of that step.
The second bar is the one that can fail while the first passes, because a
predictor anchored at roughly the right level can still get the slope wrong.
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

a2 = __import__("importlib").import_module("20-a2-m66-replication")
p2mod = __import__("importlib").import_module("40-p2-predictor")

# M66 fact 9, quoted from docs/research/M66-gate-n-dependence.md:158-163.
M66_FACT9 = {"mean": 0.018446, "median": 0.018739, "p05": 0.014232,
             "p95": 0.021563, "rho0": 1.2124, "rho1": 1.2122,
             "span_lo": 0.94, "span_hi": 1.42}
M66_FACT10_REAL = 0.018137


def stats(sd):
    return {
        "mean": float(np.mean(sd)),
        "median": float(np.median(sd)),
        "p05": float(np.percentile(sd, 5)),
        "p95": float(np.percentile(sd, 95)),
        "rho": float(np.mean(sd) / m69.FOCUS_NOISE_SD),
    }


def frozen(latent, iso, k, seed=1000):
    """L_k -- the same latent with k-1 EXTRA frozen noise realisations."""
    if k == 1:
        return latent
    sd_dn = a2.raw_noise_sd(latent, iso)
    rng = np.random.default_rng(seed)
    out = latent.astype(np.float64).copy()
    for _ in range(k - 1):
        out = out + sd_dn * rng.standard_normal(latent.shape)
    return out


def p2_rho(latent, iso):
    luma = m69.luma_from_raw(latent)
    sig = m69.green_luma_sigma(luma, iso)
    return float(np.mean(m69.interior(p2mod.p2(luma, sig))) / m69.FOCUS_NOISE_SD)


def p2_rho_debiased(latent, iso, k):
    """P2 at k = 0: strip k * 2 s^2 from the observed gradient budget.

    The latent's gradient is rescaled isotropically so that its mean square
    drops by exactly the k realisations' contribution. Direction is preserved,
    which is what the mechanism of section 6 says matters.
    """
    luma = m69.luma_from_raw(latent)
    sig = m69.green_luma_sigma(luma, iso)
    gx, gy = m69.sobel_components(luma)
    s = p2mod.S_SOBEL * sig
    nu2 = gx * gx + gy * gy
    nu2d = np.maximum(nu2 - k * 2.0 * s * s, 0.0)
    scale = np.sqrt(np.divide(nu2d, np.maximum(nu2, 1e-30)))
    return float(np.mean(m69.interior(
        p2mod.p2_scaled(luma, sig, scale))) / m69.FOCUS_NOISE_SD)


def main():
    nrep = int(sys.argv[1]) if len(sys.argv) > 1 else 299
    m69.banner("M69 arm A7 -- M66 fact 9, and the frozen-latent control")
    m69.dump_constants()

    stack, name, y, x = a2.M62_PLANT
    latent, path, y, x = a2.read_latent(stack, name, y, x)
    iso = m69.iso_of(path)
    print(f"\n  plant: {path}")
    print(f"  crop {latent.shape} at (y={y}, x={x}), ISO {iso}, N = {nrep}\n")

    m69.banner("A7.1 -- reproducing M66 fact 9 (temporal estimator, N = 299)")
    print(f"  {'seed':>5} {'mean':>10} {'median':>10} {'p05':>10} {'p95':>10} {'rho':>8}")
    print("  " + "-" * 58)
    seeds = {}
    for seed in (0, 1):
        sd, _ = a2.temporal_sd(latent, iso, nrep, seed)
        st = stats(sd)
        seeds[seed] = st
        print(f"  {seed:>5} {st['mean']:>10.6f} {st['median']:>10.6f}"
              f" {st['p05']:>10.6f} {st['p95']:>10.6f} {st['rho']:>8.4f}")
    print(f"  {'M66':>5} {M66_FACT9['mean']:>10.6f} {M66_FACT9['median']:>10.6f}"
          f" {M66_FACT9['p05']:>10.6f} {M66_FACT9['p95']:>10.6f}"
          f" {M66_FACT9['rho0']:>8.4f}   <- M66 fact 9, seed 0")
    d0 = seeds[0]["rho"] - M66_FACT9["rho0"]
    d1 = seeds[1]["rho"] - M66_FACT9["rho1"]
    print(f"\n  delta vs M66 fact 9:  seed 0 {d0:+.4f}   seed 1 {d1:+.4f}"
          f"   (D1 bar was +-0.02)")
    print(f"  note M66's own two estimators on this ONE plant differ:"
          f" fact 9 mean {M66_FACT9['mean']:.6f} vs fact 10 REAL"
          f" {M66_FACT10_REAL:.6f}"
          f"  ({M66_FACT9['mean'] / M66_FACT10_REAL - 1:+.2%})")

    m69.banner("A7.2 -- the control: k frozen noise realisations")
    print("  k = 1 is M66's plant. Each extra k adds exactly 2 s^2 of spurious")
    print("  gradient -- the same quantity the freeze already added once.\n")
    print(f"  {'k':>3} {'rho measured':>13} {'P2 predicted':>13} {'abs err':>9}")
    print("  " + "-" * 42)
    ks = (1, 2, 3)
    meas, pred = {}, {}
    for k in ks:
        Lk = frozen(latent, iso, k)
        sd, _ = a2.temporal_sd(Lk, iso, nrep, 0)
        meas[k] = float(np.mean(sd) / m69.FOCUS_NOISE_SD)
        pred[k] = p2_rho(Lk, iso)
        print(f"  {k:>3} {meas[k]:>13.4f} {pred[k]:>13.4f}"
              f" {pred[k] - meas[k]:>+9.4f}")

    step_m = meas[3] - meas[1]
    step_p = pred[3] - pred[1]
    lvl_ok = all(abs(pred[k] - meas[k]) <= 0.05 for k in ks)
    step_ok = abs(step_p - step_m) <= 0.30 * abs(step_m) if step_m != 0 else False
    print(f"\n  level  : worst |P2 - measured| ="
          f" {max(abs(pred[k] - meas[k]) for k in ks):.4f}   bar 0.05"
          f"  ->  {'MET' if lvl_ok else 'NOT MET'}")
    print(f"  slope  : measured step k=1->3 {step_m:+.4f}, P2 {step_p:+.4f},"
          f" miss {abs(step_p - step_m):.4f}   bar {0.30 * abs(step_m):.4f}"
          f"  ->  {'MET' if step_ok else 'NOT MET'}")

    m69.banner("A7.3 -- back-extrapolation to k = 0, the plant nobody can build")
    lin = meas[1] - (meas[2] - meas[1])
    quad = 3.0 * meas[1] - 3.0 * meas[2] + meas[3]
    p2_0 = p2_rho_debiased(latent, iso, 1)
    print(f"  linear back-step from k=1,2      rho(0) = {lin:.4f}")
    print(f"  quadratic back-step from k=1,2,3 rho(0) = {quad:.4f}")
    print(f"  P2 on the debiased gradient      rho(0) = {p2_0:.4f}")
    print(f"\n  M66 published 1.2124 for this plant. The defect-free value this")
    print(f"  arm puts under it is {p2_0:.4f}, bracketed by {min(lin, quad):.4f}"
          f"-{max(lin, quad):.4f} from the measured ladder alone.")

    (m69.OUT / "95-a7.json").write_text(json.dumps({
        "nrep": nrep, "iso": iso, "plant": path,
        "seeds": {str(k): v for k, v in seeds.items()},
        "m66_fact9": M66_FACT9,
        "frozen": {"measured": {str(k): meas[k] for k in ks},
                   "p2": {str(k): pred[k] for k in ks},
                   "step_measured": step_m, "step_p2": step_p,
                   "level_met": bool(lvl_ok), "slope_met": bool(step_ok)},
        "back_extrapolation": {"linear": lin, "quadratic": quad, "p2": p2_0},
    }, indent=2), encoding="utf-8")
    print("\n  wrote out/95-a7.json")


if __name__ == "__main__":
    main()

