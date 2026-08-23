"""31 -- hold M25's plant fixed, swap only the statistic.

PRE-REGISTERED in PREREGISTRATION-B.md section 4 (T1, T2, T3), committed
b28b2e3 before this script existed.

Four published probes attacked fact 568's wrong sign and every one varied the
PLANT.  This varies the INSTRUMENT and nothing else: the frames, the truth
planes, the focus fields, the `strong` gate and the veiled/smooth populations
are all computed once and shared by every statistic below.

  S0  M21's multipeak, copied verbatim.  Peak must clear both neighbours by
      0.04 x (max - min) of that pixel's own through-focus curve.
  S1  the SAME function with one line changed: the threshold becomes
      z* x sigma_pred from the project's calibrated noise model, with z*
      solved for a 1% false-positive rate on a noise-only null cube.
  S2  M60's prominence-over-noise, an independent peak-finder, so the result
      does not depend on M21's peak rule either.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/M60-bimodality/src/31-swap.py
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
from scipy.ndimage import median_filter, sobel, uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m60lib as L                                               # noqa: E402

DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
PLANT = os.path.join(DATA, "30-m25-plant.npz")
OUT = os.path.join(DATA, "31-swap.txt")
OUTJ = os.path.join(DATA, "31-swap.json")

MC_REPS = 24
FPR = 0.01
MIN_BIN = 500        # M25's floor
POWER_BIN = 5000     # PREREGISTRATION-B section 6
SEED = 20260823

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


# ---------------------------------------------------------------------------
# M21's two functions, copied verbatim from
# experiments/m21-occlusion-bimodality/src/03-permutation-placebo.py
# ---------------------------------------------------------------------------
def ff(g, R):
    gx = sobel(g, axis=1, mode='reflect') / 8.0
    gy = sobel(g, axis=0, mode='reflect') / 8.0
    return uniform_filter(np.sqrt(gx * gx + gy * gy), 2 * R + 1)


def multipeak(V, thr=0.04):
    Vs = np.copy(V)
    Vs[1:-1] = (V[:-2] + 2 * V[1:-1] + V[2:]) / 4.0
    mx = Vs.max(0)
    mn = Vs.min(0)
    rng = np.maximum(mx - mn, 1e-6)
    ispk = np.zeros_like(Vs, bool)
    ispk[1:-1] = (Vs[1:-1] > Vs[:-2] + thr * rng) & (Vs[1:-1] > Vs[2:] + thr * rng)
    return ispk.sum(0) >= 2, (mx - mn) / np.maximum(mx, 1e-6), np.argmax(Vs, 0)


# ---------------------------------------------------------------------------
# S1: the SAME function, with `thr * rng` replaced by an absolute per-pixel
# threshold map.  Every other line is identical to multipeak() above.
# ---------------------------------------------------------------------------
def multipeak_abs(V, tmap):
    Vs = np.copy(V)
    Vs[1:-1] = (V[:-2] + 2 * V[1:-1] + V[2:]) / 4.0
    ispk = np.zeros_like(Vs, bool)
    ispk[1:-1] = (Vs[1:-1] > Vs[:-2] + tmap) & (Vs[1:-1] > Vs[2:] + tmap)
    return ispk.sum(0) >= 2


def enrich(mp, hi, lo):
    """M25's enrich(), verbatim in behaviour."""
    if hi.sum() < MIN_BIN or lo.sum() < MIN_BIN:
        return float("nan"), float("nan"), float("nan")
    a = mp[hi].mean() * 100.0
    b = mp[lo].mean() * 100.0
    return a, b, a / max(b, 1e-9)


def solve_z(Vnull, sigf, target):
    """Smallest z giving <= `target` false-positive rate on the null cube."""
    lo, hi = 0.05, 60.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        r = multipeak_abs(Vnull, mid * sigf).mean()
        if r > target:
            lo = mid
        else:
            hi = mid
    return hi


def main() -> None:
    t0 = time.time()
    rng0 = np.random.default_rng(SEED)
    d = np.load(PLANT)
    G = d["frames"]
    vf = d["visible_focus"]
    af = d["alpha_front"]
    iso = float(d["iso"])
    n = G.shape[0]

    say("M60b/31 -- M25's control plant held fixed, statistic swapped")
    say(f"plant: {G.shape} frames, ISO {iso:.0f}, "
        f"fg idx {float(d['near']):.0f} / bg idx {float(d['far']):.0f}, "
        f"coc {float(d['coc']):.1f} px/frame")
    say("PRE-REGISTERED PREREGISTRATION-B.md section 4, commit b28b2e3.")
    say()

    # --- shared: focus fields, gate, populations. Computed ONCE. -----------
    V2 = np.stack([ff(G[k], 2) for k in range(n)])
    V13 = np.stack([ff(G[k], 13) for k in range(n)])
    _, c13, am13 = multipeak(V13)
    amr = median_filter(am13.astype(np.float32), 5)
    step = np.abs(np.gradient(amr)[0]) + np.abs(np.gradient(amr)[1])
    strong = c13 > 0.10

    tstep = (np.abs(np.gradient(vf)[0]) + np.abs(np.gradient(vf)[1])) >= 1.0
    tpartial = (af > 0.02) & (af < 0.98)
    veiled = strong & tpartial
    smooth = strong & ~tstep & ~tpartial

    # --- POWER, asserted before any rate is read (section 6) --------------
    nv, ns = int(veiled.sum()), int(smooth.sum())
    say("POWER, asserted before any rate is interpreted:")
    say(f"  strong pixels      {int(strong.sum()):>8}  "
        f"({strong.mean()*100:.1f}% of frame)")
    say(f"  veiled (truth)     {nv:>8}")
    say(f"  smooth (truth)     {ns:>8}")
    smaller = min(nv, ns)
    assert smaller >= MIN_BIN, f"below M25's own floor of {MIN_BIN}"
    powered = smaller >= POWER_BIN
    if powered:
        p = 0.05
        sd_pp = 100.0 * np.sqrt(p * (1 - p) / smaller)
        say(f"  smaller bin {smaller} >= {POWER_BIN} -> POWERED. "
            f"binomial sd at a 5% rate = {sd_pp:.3f} pp, so a 1.5x "
            f"enrichment (5.0 -> 7.5%) is {2.5/sd_pp:.0f} sd.")
    else:
        say(f"  smaller bin {smaller} < {POWER_BIN} -> UNDERPOWERED; "
            "enrichment reported but NOT used in the verdict.")
    say()

    # --- the noise-only null and z*, for S1 and S2 ------------------------
    Ibar = G.mean(0)
    sd_dn = L.sigma_dn(Ibar, iso)
    say(f"noise model at ISO {iso:.0f}: g={L.gain_dn_per_e(iso):.5f} DN/e-, "
        f"RN={L.read_noise_e(iso):.4f} e-, median sigma(I) "
        f"{np.median(sd_dn):.2f} DN")
    Vnull = np.stack([ff(Ibar + rng0.normal(0, 1, Ibar.shape).astype(np.float32) * sd_dn, 2)
                      for _ in range(n)])
    sigf = L.focus_sigma_mc(Ibar, 2, iso, MC_REPS, rng0)
    say(f"sigma_f (MC, {MC_REPS} reps) median {np.median(sigf):.3f} DN")

    z1 = solve_z(Vnull, sigf, FPR)
    say(f"S1 z* solved on the noise-only null for {FPR*100:.0f}% FPR: "
        f"z* = {z1:.3f}  (null rate {multipeak_abs(Vnull, z1*sigf).mean()*100:.2f}%)")

    # S2 threshold, same null, same target
    Snull = np.repeat(sigf[None], n, 0)
    rn = L.second_peak(Vnull)
    zn, _, _, _ = L.prominence_z(Vnull, Snull, rn)
    z2 = float(np.quantile(zn, 1.0 - FPR))
    say(f"S2 z* from the same null at the same FPR: z* = {z2:.3f}")
    say()

    # --- T2, the mechanism, measured directly -----------------------------
    Vs = np.copy(V2)
    Vs[1:-1] = (V2[:-2] + 2 * V2[1:-1] + V2[2:]) / 4.0
    rngmap = Vs.max(0) - Vs.min(0)
    rv, rs = float(np.median(rngmap[veiled])), float(np.median(rngmap[smooth]))
    say("T2  THE MECHANISM -- is S0's denominator inflated where occlusion is?")
    say(f"  median rng (S0's denominator) at veiled pixels : {rv:8.3f} DN")
    say(f"  median rng at smooth pixels                    : {rs:8.3f} DN")
    say(f"  ratio veiled:smooth                            : {rv/max(rs,1e-9):8.3f}x")
    t2 = rv / max(rs, 1e-9)
    if t2 >= 1.5:
        say("  -> >= 1.5x: denominator IS materially inflated at veiled pixels. "
            "H-A supported.")
    elif 0.8 <= t2 <= 1.25:
        say("  -> in 0.8-1.25: H-A REFUTED as a mechanism, whatever T1 shows.")
    else:
        say("  -> between the registered bands; report as indeterminate.")
    say(f"  absolute threshold this implies: 0.04*rng = "
        f"{0.04*rv:.3f} DN at veiled vs {0.04*rs:.3f} DN at smooth")
    say(f"  for comparison, S1's absolute threshold is z*.sigma_f = "
        f"{z1*float(np.median(sigf)):.3f} DN (median)")
    say()

    # --- T1, primary -------------------------------------------------------
    say("T1  PRIMARY -- truth-gated veiling enrichment, M25's exact gate")
    say(f"{'statistic':<34}{'veiled%':>9}{'smooth%':>9}{'enrich':>9}"
        f"{'placebo':>9}{'base%':>8}")
    perm = rng0.permutation(n)
    res = {}
    for sid, mp, mpp in (
        ("S0  M21 verbatim (0.04*rng)", multipeak(V2)[0], multipeak(V2[perm])[0]),
        ("S1  same, noise-thresholded", multipeak_abs(V2, z1 * sigf),
         multipeak_abs(V2[perm], z1 * sigf)),
    ):
        a, b, e = enrich(mp, veiled, smooth)
        _, _, pe = enrich(mpp, veiled, smooth)
        base = mp[strong].mean() * 100.0
        say(f"{sid:<34}{a:9.2f}{b:9.2f}{e:9.2f}{pe:9.2f}{base:8.1f}")
        res[sid.split()[0]] = dict(veiled=a, smooth=b, enrich=e, placebo=pe,
                                   base=base)

    # S2
    S = np.repeat(sigf[None], n, 0)
    r2 = L.second_peak(V2)
    zz, prom, den, kd = L.prominence_z(V2, S, r2)
    mp2 = zz > z2
    r2p = L.second_peak(V2[perm])
    zzp, _, _, _ = L.prominence_z(V2[perm], S, r2p)
    a, b, e = enrich(mp2, veiled, smooth)
    _, _, pe = enrich(zzp > z2, veiled, smooth)
    base = mp2[strong].mean() * 100.0
    say(f"{'S2  M60 prominence-over-noise':<34}{a:9.2f}{b:9.2f}{e:9.2f}"
        f"{pe:9.2f}{base:8.1f}")
    res["S2"] = dict(veiled=a, smooth=b, enrich=e, placebo=pe, base=base)
    say()

    # numerator/denominator published separately (rule 39 / discipline 338)
    say("  numerator and denominator, published separately (rule 39):")
    say(f"    S2 prominence  veiled {np.median(prom[veiled]):7.3f} DN   "
        f"smooth {np.median(prom[smooth]):7.3f} DN")
    say(f"    S2 denominator veiled {np.median(den[veiled]):7.3f} DN   "
        f"smooth {np.median(den[smooth]):7.3f} DN")
    say()

    # --- invalidating conditions, checked before the verdict --------------
    say("Invalidating conditions (M25's, adopted unchanged):")
    ok = True
    for k, v in res.items():
        pl_ok = abs(v["placebo"] - 1.0) <= 0.15
        sat_ok = v["base"] <= 90.0
        say(f"  {k}: placebo {v['placebo']:.2f} "
            f"{'OK' if pl_ok else 'OUT OF BAND'}   base {v['base']:.1f}% "
            f"{'OK' if sat_ok else 'SATURATED >90%, uninterpretable'}")
        ok = ok and pl_ok and sat_ok
    say()

    # --- verdict, by the pre-registered rule --------------------------------
    s0, s1, s2 = res["S0"]["enrich"], res["S1"]["enrich"], res["S2"]["enrich"]
    say("T1 VERDICT by the pre-registered rule:")
    if not np.isfinite(s0) or s0 >= 1.0:
        v = "AMBIGUOUS -- failed to reproduce M25's wrong sign"
    elif max(s1, s2) >= 1.5:
        v = "INSTRUMENT -- fact 568's conclusion is VOID"
    elif s1 < 1.0 and s2 < 1.0:
        v = "PLANT -- fact 568 STANDS"
    else:
        v = "PARTIAL -- both contribute"
    say(f"  S0={s0:.2f}x  S1={s1:.2f}x  S2={s2:.2f}x  ->  {v}")
    if not ok:
        say("  NOTE: at least one invalidating condition fired; see above.")
    say()

    # --- T3, threshold sweep with the saturation guard ---------------------
    say("T3  threshold sweep on S0's own thr, with the registered "
        "90% saturation guard")
    say(f"{'thr':>8}{'veiled%':>10}{'smooth%':>10}{'enrich':>9}{'base%':>8}  guard")
    sweep = []
    for thr in (0.04, 0.02, 0.01, 0.005, 0.002, 0.0):
        mp, _, _ = multipeak(V2, thr=thr)
        a, b, e = enrich(mp, veiled, smooth)
        base = mp[strong].mean() * 100.0
        g = "SATURATED" if base > 90.0 else "ok"
        say(f"{thr:8.3f}{a:10.2f}{b:10.2f}{e:9.2f}{base:8.1f}  {g}")
        sweep.append(dict(thr=thr, veiled=a, smooth=b, enrich=e, base=base,
                          saturated=bool(base > 90.0)))
    say()
    say(f"total {time.time()-t0:.0f}s")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    with open(OUTJ, "w", encoding="utf-8") as fh:
        json.dump(dict(power=dict(strong=int(strong.sum()), veiled=nv,
                                  smooth=ns, powered=bool(powered)),
                       z1=z1, z2=z2, t2_ratio=t2, rng_veiled=rv,
                       rng_smooth=rs, stats=res, sweep=sweep, verdict=v),
                  fh, indent=1)


if __name__ == "__main__":
    main()
