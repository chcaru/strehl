r"""M75 step 3 -- adjudicate K0-K5 and A1-A2 against the pre-registration.

Committed before running, and written while src/02-band-sweep.py was still in
flight, so no band-resolved number existed anywhere when the thresholds in
src/01-preregistration.py were turned into code.

Every gate prints its estimator, its band and its verdict.  Both branches of
every gate are implemented; a gate that fires against my own prior (H2) is
reported as such.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
M72SRC = HERE.parent.parent / "M72-green-correlation" / "src"
DATA = HERE.parent / "data"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


m72 = _load("m72", M72SRC / "01-green-correlation.py")
m72c = _load("m72c", M72SRC / "02-criteria.py")
pre = _load("pre", HERE / "01-preregistration.py")

NBAND = pre.NBAND
PRIMARY = "k6"
SH = 400
RNG = np.random.default_rng(20250918)

M68_RG1 = -0.0659
M68_BG2 = -0.0625
K1_TOL = 0.0200
A1_BAND = 0.0220
K3_CORR = 0.70
K4_MAX_SD = 0.233

OUT: list[str] = []


def say(s: str = "") -> None:
    print(s)
    OUT.append(s)


def rule(t: str) -> None:
    say("")
    say("=" * 78)
    say(t)
    say("=" * 78)


def floor_of(y: np.ndarray) -> float:
    """N_grad: sd of E_trend under band-label shuffling."""
    return pre.ngrad_floor(np.asarray(y, float), SH, RNG)


def main() -> int:
    blob = json.loads((DATA / "02-band-sweep.json").read_text(encoding="utf-8"))
    groups = sorted(blob["groups"], key=lambda g: g["iso"])
    isos = [g["iso"] for g in groups]
    g_arr = np.array([m72c.gain(i) for i in isos])
    md_arr = np.array([m72c.mode(i) for i in isos])
    T = groups[0]["T"]
    say(f"M75 criteria.  {len(groups)} ISO groups: {isos}")
    say(f"T = {T} frames per group, {NBAND} bands, primary arm {PRIMARY}")
    say(f"estimators: E_alpha=fit_alpha_delta[alpha_high], E_rho=rho_from"
        f"[sheppard], E_trend=OLS slope*{NBAND}, E_defect=defect_flags")

    def alpha_prof(axis: str, arm: str, plane: str, key: str = "alpha_high"):
        out = np.empty(NBAND)
        for b in range(NBAND):
            y = np.array([gg["axes"][axis][arm]["planes"][plane]["var"][b]
                          for gg in groups])
            out[b] = m72c.fit_alpha_delta(g_arr, md_arr, y)[key]
        return out

    def rho_prof(axis: str, arm: str, pair: str, perm: bool = False):
        out = np.empty(NBAND)
        for b in range(NBAND):
            c = np.mean([gg["axes"][axis][arm]["pairs"][pair]
                         ["cov_perm" if perm else "cov"][b] for gg in groups])
            va = np.mean([gg["axes"][axis][arm]["pairs"][pair]["var_a"][b]
                          for gg in groups])
            vb = np.mean([gg["axes"][axis][arm]["pairs"][pair]["var_b"][b]
                          for gg in groups])
            out[b] = m72.rho_from(va, vb, c, True)
        return out

    def rho_prof_iso(axis, arm, pair, gi, perm=False):
        gg = groups[gi]
        e = gg["axes"][axis][arm]["pairs"][pair]
        return np.array([m72.rho_from(e["var_a"][b], e["var_b"][b],
                                      e["cov_perm" if perm else "cov"][b], True)
                         for b in range(NBAND)])

    # ---------------------------------------------------------------- K0 ----
    rule("K0  NOISE FLOOR  (N_grad, band-label shuffle, adversarial)")
    say("BAND: a trend counts as real only if |trend| > 3 * N_grad sd.")
    say("VOID CONDITION: alpha-arm N_grad sd > 0.0220 means the instrument")
    say("cannot resolve M68's own -0.0659 effect.")
    ratio_prof = {}
    for num, den in (("B", "G2"), ("B", "G1"), ("R", "G1"), ("R", "G2"),
                     ("G2", "G1"), ("R", "B")):
        ratio_prof[f"{num}/{den}"] = (alpha_prof("row", PRIMARY, num)
                                      / alpha_prof("row", PRIMARY, den))
    floors = {}
    say("")
    say(f"{'statistic':>10s} {'trend':>10s} {'r':>8s} {'N_grad sd':>11s} "
        f"{'3sd':>9s} {'real?':>7s}")
    for k, v in ratio_prof.items():
        tr, r = pre.trend(v)
        f = floor_of(v)
        floors[k] = f
        say(f"{k:>10s} {tr:>+10.4f} {r:>+8.3f} {f:>11.5f} {3*f:>9.5f} "
            f"{'yes' if abs(tr) > 3*f else 'NO':>7s}")
    alpha_floor = max(floors[k] for k in ("B/G2", "R/G1"))
    k0_ok = alpha_floor <= A1_BAND
    say("")
    say(f"K0 alpha arm: worst N_grad sd on the two signal ratios "
        f"{alpha_floor:.5f} vs void threshold {A1_BAND}")
    say(f"K0 VERDICT: {'MET -- gradient arm proceeds' if k0_ok else 'NOT MET -- gradient arm VOID'}")

    # ---------------------------------------------------------------- A1 ----
    rule("A1  ADVERSARIAL: does E_alpha manufacture a gradient from a pure scale?")
    say("Motivation: G2/G1 flat is a CONFIRMING control comparing planes with")
    say("EQUAL alpha; the signal ratios compare planes with alpha ratio 0.85.")
    say("A bias that cancels at 1.00 but not 0.85 would make the control flat")
    say("and the signal sloped with no physical gradient (discipline 496).")
    npix = int(np.median(groups[0]["axes"]["row"][PRIMARY]["planes"]["G2"]["n"]))
    say(f"BAND: |trend| < {A1_BAND} on planted ratio 0.85, no gradient,")
    say(f"      real per-band surviving pixel count n = {npix}")
    a1 = pre.plant_ratio_no_gradient(0.85, min(npix, 60000), RNG)
    a1_ok = abs(a1["trend"]) < A1_BAND
    say(f"  planted mean {a1['mean']:.5f}  trend {a1['trend']:+.5f}  "
        f"r {a1['r']:+.3f}  spread {a1['spread']:.5f}")
    say(f"A1 VERDICT: {'MET -- estimator clean at the ratio that matters' if a1_ok else 'NOT MET -- M68 E1 and M75 O2 are BOTH estimator artefacts'}")

    # ---------------------------------------------------------------- A2 ----
    rule("A2  ADVERSARIAL: does a row-dependent defect density manufacture both?")
    say("Discipline 497: plant against the bias that FLATTERS. H1 is flattered")
    say("by anything giving both statistics a common row profile.")
    say("")
    say("per-band surviving fraction under E_defect k=6, by plane:")
    for p in m72.PLANES:
        n = np.array(groups[0]["axes"]["row"][PRIMARY]["planes"][p]["n"], float)
        ntot = np.array(groups[0]["axes"]["row"]["none"]["planes"][p]["n"], float)
        fr = n / ntot
        tr, r = pre.trend(fr)
        say(f"  {p:>3s}  frac {fr.min():.5f}..{fr.max():.5f}  "
            f"trend {tr:+.5f}  r {r:+.3f}")
    say("")
    say("arm stability of the alpha-ratio trend (band: move < 0.0220):")
    arm_tr = {}
    for arm in blob["arms"]:
        row = []
        for num, den in (("B", "G2"), ("R", "G1"), ("G2", "G1")):
            tr, _ = pre.trend(alpha_prof("row", arm, num)
                              / alpha_prof("row", arm, den))
            row.append(tr)
        arm_tr[arm] = row
        say(f"  {arm:>5s}  B/G2 {row[0]:+.4f}  R/G1 {row[1]:+.4f}  "
            f"G2/G1 {row[2]:+.4f}")
    span_a = max(max(v[i] for v in arm_tr.values()) - min(v[i] for v in arm_tr.values())
                 for i in (0, 1))
    say(f"  worst movement across arms: {span_a:.5f}")
    say("")
    say("arm stability of the rho band trend (band: move < 3 * N_grad sd):")
    rho_arm = {}
    for arm in blob["arms"]:
        row = {}
        for a, b, _ in m72.PAIRS:
            k = f"{a}-{b}"
            row[k] = pre.trend(rho_prof("row", arm, k))[0]
        rho_arm[arm] = row
        say("  " + f"{arm:>5s}  " + "  ".join(f"{k} {v:+.5f}"
                                              for k, v in row.items()))
    rho_floor = {f"{a}-{b}": floor_of(rho_prof("row", PRIMARY, f"{a}-{b}"))
                 for a, b, _ in m72.PAIRS}
    span_r = {k: max(rho_arm[a][k] for a in blob["arms"])
              - min(rho_arm[a][k] for a in blob["arms"]) for k in rho_floor}
    worst = max(span_r[k] / (3 * rho_floor[k]) for k in rho_floor)
    say(f"  worst rho movement / its own 3-sigma floor: {worst:.2f}")
    a2_ok = span_a < A1_BAND and worst < 1.0
    say(f"A2 VERDICT: {'MET -- arm-independent, shared-profile test interpretable' if a2_ok else 'NOT MET -- shared profile attributable to the defect layer'}")

    # ---------------------------------------------------------------- K1 ----
    rule("K1  REPRODUCTION of M68 E1  (E_alpha, E_trend, 32 row bands, arm k6)")
    tr_rg1, r_rg1 = pre.trend(ratio_prof["R/G1"])
    tr_bg2, r_bg2 = pre.trend(ratio_prof["B/G2"])
    tr_gg, r_gg = pre.trend(ratio_prof["G2/G1"])
    say(f"BAND: R/G1 within +/-{K1_TOL} of {M68_RG1}, B/G2 within +/-{K1_TOL} "
        f"of {M68_BG2}, both |r| > 0.70")
    say(f"  R/G1  M68 {M68_RG1:+.4f}  M75 {tr_rg1:+.4f}  "
        f"delta {tr_rg1 - M68_RG1:+.4f}  r {r_rg1:+.3f}")
    say(f"  B/G2  M68 {M68_BG2:+.4f}  M75 {tr_bg2:+.4f}  "
        f"delta {tr_bg2 - M68_BG2:+.4f}  r {r_bg2:+.3f}")
    say(f"  G2/G1 M68 {+0.0028:+.4f}  M75 {tr_gg:+.4f}  (N_gain control)")
    k1_ok = (abs(tr_rg1 - M68_RG1) < K1_TOL and abs(tr_bg2 - M68_BG2) < K1_TOL
             and abs(r_rg1) > 0.70 and abs(r_bg2) > 0.70)
    say(f"K1 VERDICT: {'MET -- M68 E1 independently reproduced' if k1_ok else 'NOT MET -- cross-milestone comparison VOID, discrepancy is the result'}")

    # ---------------------------------------------------------------- K5 ----
    rule("K5  WHICH PLANES ACTUALLY MOVE  (O1: ABSOLUTE alpha per band)")
    say("A ratio measures only a DIFFERENCE of slopes (pre-reg section 1.1).")
    say("BAND: a plane moves if its normalised trend exceeds its 3-sigma floor.")
    absol, moves = {}, {}
    say("")
    say(f"{'plane':>6s} {'alpha_high':>11s} {'norm trend':>11s} {'r':>8s} "
        f"{'3*N_grad':>10s} {'moves?':>8s}")
    for p in m72.PLANES:
        a = alpha_prof("row", PRIMARY, p)
        absol[p] = a
        nrm = a / a.mean()
        tr, r = pre.trend(nrm)
        f3 = 3 * floor_of(nrm)
        moves[p] = abs(tr) > f3
        say(f"{p:>6s} {a.mean():>11.5f} {tr:>+11.5f} {r:>+8.3f} {f3:>10.5f} "
            f"{'YES' if moves[p] else 'no':>8s}")
    say("")
    say("same for alpha_low and for delta (supporting, not gated):")
    for key in ("alpha_low", "delta"):
        row = []
        for p in m72.PLANES:
            a = alpha_prof("row", PRIMARY, p, key)
            row.append(f"{p} {pre.trend(a / a.mean())[0]:+.4f}")
        say(f"  {key:>10s}  " + "  ".join(row))
    green_moves = moves["G1"] or moves["G2"]
    chroma_moves = moves["R"] or moves["B"]
    if green_moves and not chroma_moves:
        k5 = "H5 HOLDS -- the GREENS move, R and B do not. M68's description of its own finding is inverted."
    elif chroma_moves and not green_moves:
        k5 = "M68's description CONFIRMED -- R and B move, greens flat."
    elif chroma_moves and green_moves:
        k5 = "ALL planes move -- the ratio effect is a difference of slopes on a common background."
    else:
        k5 = "NO plane moves above its own floor -- the ratio effect has no absolute counterpart."
    say(f"K5 VERDICT: {k5}")

    # ---------------------------------------------------------------- K2 ----
    rule("K2  GROUPING  (does each statistic select the same bipartition?)")
    say("N.B. the greens are a GAIN null, NOT an independence null "
        "(SYNTHESIS fact 1034);")
    say("N_gain is used in the alpha arm only and appears nowhere in the rho arm.")
    say("")
    say("alpha arm -- normalised absolute band trend per plane:")
    av = {p: pre.trend(absol[p] / absol[p].mean())[0] for p in m72.PLANES}
    for p in m72.PLANES:
        say(f"  {p:>3s} {av[p]:+.5f}")
    say("")
    say("rho arm -- pooled rho per pair (whole sensor, primary arm):")
    pooled = {}
    for a, b, cls in m72.PAIRS:
        k = f"{a}-{b}"
        c = np.mean([np.average(gg["axes"]["row"][PRIMARY]["pairs"][k]["cov"],
                                weights=gg["axes"]["row"][PRIMARY]["pairs"][k]["n"])
                     for gg in groups])
        va = np.mean([np.average(gg["axes"]["row"][PRIMARY]["pairs"][k]["var_a"],
                                 weights=gg["axes"]["row"][PRIMARY]["pairs"][k]["n"])
                      for gg in groups])
        vb = np.mean([np.average(gg["axes"]["row"][PRIMARY]["pairs"][k]["var_b"],
                                 weights=gg["axes"]["row"][PRIMARY]["pairs"][k]["n"])
                      for gg in groups])
        pooled[k] = m72.rho_from(va, vb, c, True)
        say(f"  {k:>6s} ({cls:>8s}) rho {pooled[k]:+.5f}")

    def bipart(val: dict, keyer) -> tuple:
        best, bestgap = None, -1.0
        planes = m72.PLANES
        for i in range(len(planes)):
            for j in range(i + 1, len(planes)):
                g1 = {planes[i], planes[j]}
                g2 = set(planes) - g1
                gap = keyer(val, g1, g2)
                if gap > bestgap:
                    best, bestgap = (tuple(sorted(g1)), tuple(sorted(g2))), gap
        return best, bestgap

    def alpha_key(v, g1, g2):
        a = np.mean([v[p] for p in g1])
        b = np.mean([v[p] for p in g2])
        sp = max(np.ptp([v[p] for p in g1]), np.ptp([v[p] for p in g2]))
        return abs(a - b) - sp

    def rho_key(v, g1, g2):
        within = [v[k] for k in v
                  if set(k.split("-")) <= g1 or set(k.split("-")) <= g2]
        across = [v[k] for k in v
                  if not (set(k.split("-")) <= g1 or set(k.split("-")) <= g2)]
        return np.mean(within) - np.mean(across)

    pa, ga = bipart(av, alpha_key)
    pr, gr = bipart(pooled, rho_key)
    say("")
    say(f"  alpha arm best bipartition: {pa[0]} | {pa[1]}  (separation {ga:+.5f})")
    say(f"  rho   arm best bipartition: {pr[0]} | {pr[1]}  (separation {gr:+.5f})")
    say(f"  R sits with B under alpha? "
        f"{'yes' if 'B' in (pa[0] if 'R' in pa[0] else pa[1]) else 'no'}")
    say(f"  R sits with B under rho?   "
        f"{'yes' if 'B' in (pr[0] if 'R' in pr[0] else pr[1]) else 'no'}")
    same = set(map(frozenset, pa)) == set(map(frozenset, pr))
    say(f"K2 VERDICT: partitions {'AGREE -- H1 supported, K3 tests it quantitatively' if same else 'DIFFER -- H1 loses its simplest form, K3 becomes decisive'}")

    # ---------------------------------------------------------------- K3 ----
    rule("K3  DECISIVE: SHARED SPATIAL SIGNATURE")
    say("BAND (a): rho(R-B) band trend must exceed 3 * its N_grad floor.")
    say(f"BAND (b): |corr across {NBAND} bands| > {K3_CORR} between the")
    say("          covariance profile of the implicated pair and the")
    say("          alpha-ratio profile of the same planes.")
    say("")
    say(f"{'pair':>6s} {'rho trend':>11s} {'r':>8s} {'3*N_grad':>10s} "
        f"{'real?':>7s} {'perm trend':>11s}")
    rp = {}
    for a, b, cls in m72.PAIRS:
        k = f"{a}-{b}"
        v = rho_prof("row", PRIMARY, k)
        rp[k] = v
        tr, r = pre.trend(v)
        f3 = 3 * rho_floor[k]
        ptr = pre.trend(rho_prof("row", PRIMARY, k, perm=True))[0]
        say(f"{k:>6s} {tr:>+11.5f} {r:>+8.3f} {f3:>10.5f} "
            f"{'yes' if abs(tr) > f3 else 'NO':>7s} {ptr:>+11.5f}")
    tr_rb, r_rb = pre.trend(rp["R-B"])
    k3a = abs(tr_rb) > 3 * rho_floor["R-B"]
    alpha_sig = 0.5 * (ratio_prof["R/G1"] / ratio_prof["R/G1"].mean()
                       + ratio_prof["B/G2"] / ratio_prof["B/G2"].mean())
    corr_rb = float(np.corrcoef(rp["R-B"], alpha_sig)[0, 1])
    k3b = abs(corr_rb) > K3_CORR
    say("")
    say(f"  cross-statistic band correlation, rho(R-B) vs mean(R/G1, B/G2) "
        f"alpha profile: {corr_rb:+.4f}")
    say("  full cross-statistic matrix (rho profile vs alpha-ratio profile):")
    say("  " + f"{'':>7s}" + "".join(f"{k:>9s}" for k in ratio_prof))
    for a, b, _ in m72.PAIRS:
        k = f"{a}-{b}"
        say("  " + f"{k:>7s}" + "".join(
            f"{float(np.corrcoef(rp[k], ratio_prof[q])[0,1]):>+9.3f}"
            for q in ratio_prof))

    # ---------------------------------------------------------------- K4 ----
    rule("K4  POWER  (guard against concluding H2 from a weak test)")
    say(f"BAND: N_grad sd of the K3(b) band correlation must be < {K4_MAX_SD}")
    say("      so that 0.70 is resolvable at 3 sigma.")
    cs = np.empty(SH)
    for i in range(SH):
        cs[i] = np.corrcoef(RNG.permutation(rp["R-B"]), alpha_sig)[0, 1]
    sd_c = float(cs.std(ddof=1))
    k4_ok = sd_c < K4_MAX_SD
    say(f"  N_grad sd of the band correlation: {sd_c:.4f}  "
        f"(3 sigma = {3*sd_c:.4f})")
    say(f"K4 VERDICT: {'MET -- a null in K3 is interpretable as evidence for H2' if k4_ok else 'NOT MET -- UNDERPOWERED, H2 may NOT be concluded'}")

    say("")
    if k3a and k3b:
        k3 = "BOTH MET -- one phenomenon; locate the mechanism with O4."
    elif not k3a and not k3b:
        k3 = ("NEITHER MET -- TWO PHENOMENA" if k4_ok else
              "NEITHER MET but K4 failed -- UNDERPOWERED, cannot separate")
    else:
        k3 = ("EXACTLY ONE MET -- the observable does NOT separate them; "
              "reported as such rather than picking the nearer option")
    say(f"K3 VERDICT: {k3}")
    say(f"   (a) rho(R-B) trend real: {k3a}   (b) |corr| > {K3_CORR}: {k3b}")

    # ---------------------------------------------------------------- O4 ----
    rule("O4  UPSTREAM / DOWNSTREAM location of any band-resolved covariance")
    say("M72 P1/P2: |d|=1 pairs are upstream (scale with G^2), |d|>=sqrt(2)")
    say("are downstream (flat in DN). The alpha gradient is upstream BY")
    say("CONSTRUCTION, since alpha is the G^2 coefficient. Discipline 473:")
    say("locate by where the noise is GENERATED, not where signal is scaled.")
    say("")
    say(f"{'pair':>6s} {'class':>9s} {'cov@ISO50':>11s} {'cov@ISO2000':>12s} "
        f"{'ratio':>9s} {'G^2 ratio':>10s} {'upstream f':>11s}")
    gs = (m72c.gain(isos[-1]) / m72c.gain(isos[0])) ** 2
    for a, b, cls in m72.PAIRS:
        k = f"{a}-{b}"
        c0 = np.average(groups[0]["axes"]["row"][PRIMARY]["pairs"][k]["cov"],
                        weights=groups[0]["axes"]["row"][PRIMARY]["pairs"][k]["n"])
        c1 = np.average(groups[-1]["axes"]["row"][PRIMARY]["pairs"][k]["cov"],
                        weights=groups[-1]["axes"]["row"][PRIMARY]["pairs"][k]["n"])
        f = (c1 / c0 - 1.0) / (gs - 1.0) if c0 else float("nan")
        say(f"{k:>6s} {cls:>9s} {c0:>11.5f} {c1:>12.4f} {c1/c0:>9.3f} "
            f"{gs:>10.3f} {f:>11.4f}")

    # ---------------------------------------------------------------- O5 ----
    rule("O5  COLUMN BANDS  (a row-only effect and a row+column effect differ)")
    say(f"{'statistic':>10s} {'row trend':>11s} {'col trend':>11s} {'col r':>8s}")
    for k in ("B/G2", "R/G1", "G2/G1"):
        num, den = k.split("/")
        cprof = alpha_prof("column", PRIMARY, num) / alpha_prof("column", PRIMARY, den)
        ct, cr = pre.trend(cprof)
        say(f"{k:>10s} {pre.trend(ratio_prof[k])[0]:>+11.4f} {ct:>+11.4f} "
            f"{cr:>+8.3f}")
    for a, b, _ in m72.PAIRS:
        k = f"{a}-{b}"
        ct, cr = pre.trend(rho_prof("column", PRIMARY, k))
        say(f"{k:>10s} {pre.trend(rp[k])[0]:>+11.5f} {ct:>+11.5f} {cr:>+8.3f}")

    rule("SUMMARY")
    for nm, ok in (("K0", k0_ok), ("A1", a1_ok), ("A2", a2_ok), ("K1", k1_ok),
                   ("K4", k4_ok)):
        say(f"  {nm}: {'MET' if ok else 'NOT MET'}")
    say(f"  K2: {'AGREE' if same else 'DIFFER'}")
    say(f"  K3: {k3}")
    say(f"  K5: {k5}")

    (DATA / "03-criteria.txt").write_text("\n".join(OUT) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
