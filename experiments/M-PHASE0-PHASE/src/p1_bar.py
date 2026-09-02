"""Part 1 of M-PHASE0-PHASE: derive the bar the proposal leaves blank.

`docs/proposals/2026-08-sota-path.md:1030-1034` gates C1 on "if within-DOF
relative registration cannot reach [bar] px".  The placeholder is literal; the
proposal asserts ~0.1-0.15 px twice and derives it nowhere.

This script derives it.  It needs no capture: the bar is a property of the
linear algebra plus a noise model plus the scene's alias-to-baseband ratio, so
it is computed exactly and checked against closed forms by `p0_controls.py`.

What it produces is a TRANSFER FUNCTION, `bar(kappa, rho)` -- the tolerable
displacement-error sd as a function of the site's conditioning and the scene --
because that is what the census needs.  The census can measure `kappa` per site;
it cannot measure a bar per site.

Registered by PREREGISTRATION.md section 4 and amendments A1.2, A2.2, A3.5:

  unit   median eta < 1                    conservative; beat perfect-baseband
  naive  median eta < median eta_naive     realistic; beat aligned averaging

Amendment A3 requires the output frequency `nu` to carry phase alongside the
alias offsets, and A2.4 forbids dropping configurations that have not crossed
by the end of the sigma grid -- they are counted as censored instead.

Output: out/p1_bar.json
"""

import json
import os
import sys
import time

import numpy as np

import plib

OUT = os.path.join(os.path.dirname(__file__), "..", "out", "p1_bar.json")

SIGMA_GRID = np.concatenate([[0.0], np.geomspace(1e-3, 2.0, 31)])
RHOS = [1.0, 0.3, 0.1, 0.03, 0.01]
SNRS = [("inf", np.inf), ("30dB", 30.0), ("20dB", 20.0)]
TRIALS = 1000
SAMPLES = 320
NU_GRID = 8

# G-2x and RB-2x need N >= 8 and N >= 16 sharp frames at one site, which
# section 3.1 predicted is out of reach.  Their infeasibility is reported by
# p3, not priced here; spending the compute on their bars would be spending it
# on a case the arithmetic has already excluded.
TARGET_N = {
    "G-1x": [2, 3, 4, 5, 6, 8],
    "RB-1x": [4, 5, 6, 8, 10],
}


def crossing(sigmas, values, threshold):
    """Largest sigma at which `values` is still below `threshold`.

    Returns (bar, censored).  `censored` is True when the curve never crossed
    inside the grid, in which case the bar is at least the grid maximum and the
    row is COUNTED rather than dropped (amendment A2.4).
    """
    v = np.asarray(values, dtype=float)
    t = np.asarray(threshold, dtype=float)
    t = np.full_like(v, float(t)) if t.ndim == 0 else t
    below = v < t
    if not below[0]:
        return 0.0, False
    idx = np.flatnonzero(~below)
    if idx.size == 0:
        return float(sigmas[-1]), True
    j = int(idx[0])
    s0, s1 = sigmas[j - 1], sigmas[j]
    v0, v1 = v[j - 1] - t[j - 1], v[j] - t[j]
    if v1 == v0:
        return float(s0), False
    return float(s0 + (s1 - s0) * (0.0 - v0) / (v1 - v0)), False


def sample_configs(rng, target, count):
    """Random (N, nu, d) draws spanning a wide range of conditioning.

    Uniform-random displacements are almost all well conditioned, so the
    clustering scale is drawn log-uniformly to populate the ill-conditioned
    tail, which is where the bar is most sensitive and where the census will
    actually find sites.
    """
    band = plib.band_frequencies(target, NU_GRID)
    ns = TARGET_N[target]
    out = []
    for _ in range(count):
        n = int(ns[rng.integers(len(ns))])
        nu, reps = band[int(rng.integers(len(band)))]
        scale = float(np.exp(rng.uniform(np.log(0.02), np.log(3.0))))
        d = rng.normal(0.0, scale, size=(n, 2))
        k = float(plib.kappa(reps, d))
        if not np.isfinite(k):
            continue
        out.append((n, nu, reps, d, k))
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(20260827)
    rows = []

    for target in TARGET_N:
        cfgs = sample_configs(rng, target, SAMPLES)
        for ci, (n, nu, reps, d, k) in enumerate(cfgs):
            for snr_name, snr in SNRS:
                for rho in RHOS:
                    if snr_name != "inf" and rho != 0.1:
                        continue  # the SNR ladder is run at one rho only
                    # The gauge arm (A6.2) is run noiseless; the noise gate is a
                    # separate effect and pricing it twice adds nothing.
                    gauges = ("raw", "zero_mean") if snr_name == "inf" else ("raw",)
                    for gauge in gauges:
                        e = np.empty(len(SIGMA_GRID))
                        en = np.empty(len(SIGMA_GRID))
                        for i, s in enumerate(SIGMA_GRID):
                            r = np.random.default_rng(7919 * ci + i)
                            e[i], en[i] = plib.median_eta(
                                reps, d, float(s), snr, r, TRIALS, rho=rho, nu=nu,
                                gauge=gauge)
                        bu, cu = crossing(SIGMA_GRID, e, 1.0)
                        bn, cn = crossing(SIGMA_GRID, e, en)
                        rows.append(dict(
                            target=target, N=n, M=int(reps.shape[0]),
                            kappa=k, nu_abs=float(np.hypot(*nu)),
                            snr=snr_name, rho=rho, gauge=gauge,
                            bar_unit=bu, censored_unit=bool(cu),
                            bar_naive=bn, censored_naive=bool(cn),
                            eta0=float(e[0]), eta_naive0=float(en[0]),
                        ))
        print("  %-6s %4d configs done (%.0fs)" % (target, len(cfgs), time.time() - t0))
        sys.stdout.flush()

    payload = dict(
        sigma_grid=[float(s) for s in SIGMA_GRID], trials=TRIALS,
        samples=SAMPLES, nu_grid=NU_GRID, rhos=RHOS,
        snrs=[s[0] for s in SNRS], target_n=TARGET_N,
        rows=rows, elapsed_s=time.time() - t0,
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f)

    report(rows)
    print("\nwrote %s (%.0fs)" % (os.path.normpath(OUT), payload["elapsed_s"]))
    return 0


def report(rows):
    print("\nbar vs scene ratio, noiseless, pooled over nu and N")
    print("-" * 78)
    print("  %-7s %6s %5s  %-28s %-28s %8s"
          % ("target", "rho", "n", "bar_unit RAW (px)", "bar_unit ZERO-MEAN (px)", "ratio"))
    print("  %-7s %6s %5s  %8s %8s %8s  %8s %8s %8s  %8s"
          % ("", "", "", "p10", "median", "p90", "median", "p10", "p90", "zm/raw"))
    for target in TARGET_N:
        for rho in RHOS:
            sel = [r for r in rows if r["target"] == target and r["snr"] == "inf"
                   and r["rho"] == rho and r["gauge"] == "raw"]
            selz = [r for r in rows if r["target"] == target and r["snr"] == "inf"
                    and r["rho"] == rho and r["gauge"] == "zero_mean"]
            if not sel:
                continue
            bu = np.array([r["bar_unit"] for r in sel])
            bz = np.array([r["bar_unit"] for r in selz])
            bn = np.array([r["bar_naive"] for r in sel])
            print("  %-7s %6.2f %5d  %8.4f %8.4f %8.4f  %8.4f %8.4f %8.4f  %8.4f"
                  % (target, rho, len(sel),
                     np.percentile(bu, 10), np.median(bu), np.percentile(bu, 90),
                     np.median(bz), np.percentile(bz, 10), np.percentile(bz, 90),
                     np.median(bz) / max(np.median(bu), 1e-12)))

    print("\nbar vs conditioning, rho = 0.1, noiseless")
    print("-" * 78)
    edges = [1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 1e9]
    for target in TARGET_N:
        for lo, hi in zip(edges[:-1], edges[1:]):
            sel = [r for r in rows if r["target"] == target and r["snr"] == "inf"
                   and r["rho"] == 0.1 and r["gauge"] == "raw"
                   and lo <= r["kappa"] < hi]
            if len(sel) < 3:
                continue
            bu = np.array([r["bar_unit"] for r in sel])
            k = np.array([r["kappa"] for r in sel])
            print("  %-7s kappa %5.1f-%-6.1f n=%-4d  bar_unit median %7.4f  "
                  "median kappa*bar %6.3f" % (target, lo, min(hi, 999), len(sel),
                                              np.median(bu), np.median(k * bu)))

    cens = sum(1 for r in rows if r["censored_unit"] or r["censored_naive"])
    zero = sum(1 for r in rows if r["bar_unit"] == 0.0)
    print("\n  censored (never crossed inside the grid): %d / %d" % (cens, len(rows)))
    print("  zero bar (harmful even at sigma=0):        %d / %d" % (zero, len(rows)))

    print("\nnoise ladder, rho = 0.1")
    print("-" * 78)
    for target in TARGET_N:
        line = "  %-7s" % target
        for snr in ["inf", "30dB", "20dB"]:
            sel = [r for r in rows if r["target"] == target and r["snr"] == snr
                   and r["rho"] == 0.1 and r["gauge"] == "raw"]
            if sel:
                line += "  %s: %.4f" % (snr, np.median([r["bar_unit"] for r in sel]))
        print(line)


if __name__ == "__main__":
    sys.exit(main())
