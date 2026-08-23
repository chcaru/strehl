"""M11 analysis: controls first, then the Pareto front, then the registered rule.

Standard library only, per M9's precedent. Reads only `data/*.csv` written by the
Rust harness and writes nothing outside `data/`.

Usage:  python m11_analyse.py [--out data/analysis.txt]
"""

import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

STACKS = ["109MSDCF", "119MSDCF"]
# Frames per stack, used for the chance rate of the selectivity metric.
NFRAMES = {"109MSDCF": 22, "119MSDCF": 33}

CONTROLS = ["ctl-const", "ctl-random", "ctl-luma"]
INCUMBENT = "ring-1-3"

# Registered thresholds (PREREGISTRATION.md §4). Fixed before any measurement.
N_FREE = 1.02          # membership in A
S_NEAR_BEST = 0.95     # "as selective as the best"
S_MATERIAL = 0.80      # below this, materially less selective
LAMBDA = 1.0           # registered trade-off weight in J
LAMBDA_RANGE = [0.25, 0.5, 1.0, 2.0, 4.0]

OUT = []


def say(line=""):
    OUT.append(line)
    print(line)


def load(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return float("nan")
    if n % 2:
        return xs[n // 2]
    return 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def spearman(xs, ys):
    """Spearman rho, average ranks for ties."""
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = 0.5 * (i + j) + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


# --------------------------------------------------------------------- loading

def measure_meta():
    """name -> (family, role, support_radius), from any file that carries them."""
    meta = {}
    for st in STACKS:
        for r in load(f"noise-{st}.csv"):
            meta[r["measure"]] = (r["family"], r["role"], int(r["support_radius"]))
    return meta


def noise_by_measure(fname, width="1"):
    """measure -> list of per-ROI ratios at one regulariser width."""
    d = {}
    for r in load(fname):
        if r["width"] != width:
            continue
        d.setdefault(r["measure"], []).append(float(r["ratio"]))
    return d


def planted_by_measure(fname, width="1", roi_kind="detail", field="acc", **eq):
    d = {}
    for r in load(fname):
        if r["width"] != width or r["roi_kind"] != roi_kind:
            continue
        if any(r.get(k) != v for k, v in eq.items()):
            continue
        d.setdefault(r["measure"], []).append(float(r[field]))
    return d


def stability_by_measure(fname, width="1", roi_kind="detail", field="kappa"):
    d = {}
    for r in load(fname):
        if r["width"] != width or r["roi_kind"] != roi_kind:
            continue
        d.setdefault(r["measure"], []).append(float(r[field]))
    return d


def nparams(name):
    """Free numeric knobs, counted mechanically from the registered name.

    ring-1-3 -> 2, tenengrad-w5 -> 1, brenner-sym-s2-w5 -> 2, ctl-const -> 0.
    """
    n = 0
    for tok in name.split("-"):
        digits = "".join(c for c in tok if c.isdigit())
        if digits and not tok.startswith("dct"):
            n += 1
    return n


def costs():
    d = {}
    for r in load("cost-109MSDCF.csv"):
        d[r["measure"]] = float(r["ms_per_frame_mpx"])
    return d


def roi_spread():
    """Measured ROI-to-ROI spread on each axis -- the registered O5 tie width."""
    ns, ss = [], []
    for st in STACKS:
        by = {}
        for r in load(f"noise-{st}.csv"):
            if r["width"] == "1":
                by.setdefault(r["measure"], []).append(float(r["ratio"]))
        rng = [max(v) - min(v) for v in by.values() if len(v) > 1]
        if rng:
            ns.append(median(rng))
        by = {}
        for r in load(f"planted-{st}-p1.csv"):
            if r["width"] == "1" and r["roi_kind"] == "detail":
                by.setdefault(r["measure"], []).append(float(r["acc"]))
        rng = [max(v) - min(v) for v in by.values() if len(v) > 1]
        if rng:
            ss.append(median(rng))
    return (mean(ns) if ns else 0.0), (mean(ss) if ss else 0.0)


# ------------------------------------------------------------------- reporting

def main():
    meta = measure_meta()
    if not meta:
        print("no data found in", DATA)
        return 1
    registered = [m for m, v in meta.items() if v[1] != "extension"]
    extension = [m for m, v in meta.items() if v[1] == "extension"]
    COST = costs()

    say("=" * 78)
    say("M11 -- focus-measure bake-off")
    say("=" * 78)
    say(f"registered operator set: {len(registered)}   post-hoc extension: {len(extension)}")
    say()

    # ---------------------------------------------------------- reproduction
    say("-" * 78)
    say("0. REPRODUCTION GATE (SYNTHESIS §5 item 15) -- believe the code path first")
    say("-" * 78)
    xc = os.path.join(DATA, "xcheck-109MSDCF.txt")
    if os.path.exists(xc):
        with open(xc, encoding="utf-8") as fh:
            for line in fh:
                if "ratio" in line or "published" in line:
                    say("  " + line.rstrip())
    n109 = noise_by_measure("noise-109MSDCF.csv")
    n109_17 = noise_by_measure("noise-109MSDCF.csv", width="17")
    canon = None
    for r in load("noise-109MSDCF.csv"):
        if r["measure"] == INCUMBENT and r["roi"] == "2272,1344,256,256":
            if r["width"] == "1":
                canon = float(r["ratio"])
    say(f"  ring-1-3 on M2's canonical flat ROI at width 1: {canon:.4f}x "
        f"(M2 published 1.253x, M9 reproduced 1.2527x)")
    ok = canon is not None and abs(canon - 1.2527) < 0.01 * 1.2527
    say(f"  reproduction gate: {'PASS' if ok else 'FAIL'}")
    say()

    # --------------------------------------------------------------- controls
    say("-" * 78)
    say("1. CONTROLS -- reported before any treatment")
    say("-" * 78)

    say("1a. measure-level controls, noise axis (flat ROI, width 1, median over 4 ROIs)")
    for st in STACKS:
        d = noise_by_measure(f"noise-{st}.csv")
        for c in CONTROLS:
            if c in d:
                say(f"    {st}  {c:<12} N = {median(d[c]):.4f}x   (n={len(d[c])} ROIs)")
    say("    ctl-const is the instrument floor: it always elects frame 0, so its N is")
    say("    sd(frame 0)/sd(frame middle) on that ROI and measures frame-to-frame")
    say("    scatter, not the operator.")
    say()

    say("1b. measure-level controls, selectivity axis (planted P1, detail ROIs, width 1)")
    for st in STACKS:
        d = planted_by_measure(f"planted-{st}-p1.csv")
        chance = 1.0 / NFRAMES[st]
        for c in CONTROLS:
            if c in d:
                say(f"    {st}  {c:<12} S = {median(d[c]):.4f}   (chance = {chance:.4f})")
    say()

    say("1c. P2 null -- alpha = 0, no focus planted; S must sit at chance 1/N")
    d = planted_by_measure("planted-109MSDCF-p2null.csv")
    chance = 1.0 / NFRAMES["109MSDCF"]
    vals = [(m, median(v)) for m, v in d.items() if meta.get(m, ("", "", 0))[1] == "treatment"]
    worst = max(vals, key=lambda t: t[1]) if vals else ("-", float("nan"))
    say(f"    chance = {chance:.4f}; registered threshold = {2*chance:.4f}")
    say(f"    max S over treatments = {worst[1]:.4f} ({worst[0]})")
    say(f"    median S over treatments = {median([v for _, v in vals]):.4f}")
    say(f"    P2 null gate: {'PASS' if worst[1] <= 2*chance else 'FAIL'}")
    say()

    say("1d. rule 9 pairing -- the same planted run on a FLAT ROI must collapse to chance")
    for st in STACKS:
        det = planted_by_measure(f"planted-{st}-p1.csv", roi_kind="detail")
        fl = planted_by_measure(f"planted-{st}-p1.csv", roi_kind="flat")
        ch = 1.0 / NFRAMES[st]
        tr = [m for m in det if meta.get(m, ("", "", 0))[1] == "treatment"]
        say(f"    {st}  median S over treatments: detail {median([median(det[m]) for m in tr]):.4f}"
            f"   flat {median([median(fl[m]) for m in tr if m in fl]):.4f}   chance {ch:.4f}")
        fm = max(((m, median(fl[m])) for m in tr if m in fl), key=lambda t: t[1])
        say(f"    {st}  max S on the flat ROI = {fm[1]:.4f} ({fm[0]}), "
            f"{fm[1]/ch:.2f}x chance (registered ceiling 3x)")
    say()

    say("1d-bis. constant-base null -- the amended rule 9 pairing (A5)")
    fb = planted_by_measure("planted-109MSDCF-flatbase.csv", roi_kind="flat")
    fbd = planted_by_measure("planted-109MSDCF-flatbase.csv", roi_kind="detail")
    ch = 1.0 / NFRAMES["109MSDCF"]
    for label, dd in (("flat ROI", fb), ("detail ROI", fbd)):
        if not dd:
            continue
        tr = [m for m in dd if meta.get(m, ("", "", 0))[1] == "treatment"]
        best = max(((m, median(dd[m])) for m in tr), key=lambda t: t[1])
        say(f"    {label:11s} base replaced by its own mean: max S = {best[1]:.4f} "
            f"({best[0]}), {best[1]/ch:.2f}x chance; median S = "
            f"{median([median(dd[m]) for m in tr]):.4f}")
    say(f"    chance = {ch:.4f}; registered ceiling 3x = {3*ch:.4f}")
    if fb:
        tr = [m for m in fb if meta.get(m, ("", "", 0))[1] == "treatment"]
        bv = max(median(fb[m]) for m in tr)
        say(f"    constant-base null gate: {'PASS' if bv <= 3 * ch else 'FAIL'}")
    say()

    say("1e. P0 positive control -- planted surface on a noiseless broadband texture")
    p0_0 = planted_by_measure("planted-109MSDCF-p0.csv", noise_scale="0")
    p0_1 = planted_by_measure("planted-109MSDCF-p0.csv", noise_scale="1")
    for label, dd in (("noiseless", p0_0), ("noise x1", p0_1)):
        if not dd:
            continue
        best = max(dd.items(), key=lambda t: median(t[1]))
        say(f"    {label:<10} best pointwise S = {median(best[1]):.4f} ({best[0]})")
    for w in ("9", "17"):
        dd = planted_by_measure("planted-109MSDCF-p0.csv", width=w, noise_scale="0")
        if dd:
            best = max(dd.items(), key=lambda t: median(t[1]))
            say(f"    noiseless, width {w:>2}: best S = {median(best[1]):.4f} ({best[0]})")
    say("    Registered gate (as clarified in amendment A3): the metric is valid if the")
    say("    planted surface is recovered at >= 0.90 by SOME operator/width in the set.")
    say()

    # -------------------------------------------------------------- the axes
    say("-" * 78)
    say("2. THE TWO AXES, per operator, at width 1 (the registered ranking input)")
    say("-" * 78)

    N = {}       # noise excess, mean over stacks of median over ROIs
    Ncorr = {}   # structure-corrected: coupled-G2 / placebo, same aggregation
    S = {}       # planted accuracy, mean over stacks of median over (ROI x w_true)
    K = {}       # kappa under injected noise
    KP = {}      # kappa under G1/G2
    PHI = {}
    for m in meta:
        ns, ncs, ss, ks, kps, ps = [], [], [], [], [], []
        for st in STACKS:
            d = noise_by_measure(f"noise-{st}.csv")
            if m in d:
                ns.append(median(d[m]))
            cg = noise_by_measure(f"noise-{st}-coupledg2.csv")
            pl = noise_by_measure(f"noise-{st}-placebo.csv")
            if m in cg and m in pl and median(pl[m]) > 0:
                ncs.append(median(cg[m]) / median(pl[m]))
            p = planted_by_measure(f"planted-{st}-p1.csv")
            if m in p:
                ss.append(median(p[m]))
            si = stability_by_measure(f"stability-{st}-inject.csv")
            if m in si:
                ks.append(median(si[m]))
            sp = stability_by_measure(f"stability-{st}-planes.csv")
            if m in sp:
                kps.append(median(sp[m]))
            for r in load(f"phi-{st}.csv"):
                if r["measure"] == m and r["delta"] == "8":
                    try:
                        ps.append(float(r["phi"]))
                    except ValueError:
                        pass
        if ns:
            N[m] = mean(ns)
        if ncs:
            Ncorr[m] = mean(ncs)
        if ss:
            S[m] = mean(ss)
        if ks:
            K[m] = mean(ks)
        if kps:
            KP[m] = mean(kps)
        if ps:
            PHI[m] = mean(ps)

    treat = [m for m in registered if meta[m][1] == "treatment" and m in N and m in S]
    s_max = max(S[m] for m in treat)
    s_arg = max(treat, key=lambda m: S[m])

    header = (f"{'operator':<26}{'phi':>8}{'N':>9}{'Ncorr':>9}{'S':>8}"
              f"{'S/Smax':>8}{'kappa':>8}{'k(G1G2)':>9}{'J':>8}")
    say(header)
    say("-" * len(header))
    rows = sorted(treat, key=lambda m: -S[m])
    for m in rows:
        j = (1.0 - S[m] / s_max) + LAMBDA * max(0.0, N[m] - 1.0)
        say(f"{m:<26}{PHI.get(m, float('nan')):>8.4f}{N[m]:>9.4f}"
            f"{Ncorr.get(m, float('nan')):>9.4f}{S[m]:>8.4f}{S[m]/s_max:>8.3f}"
            f"{K.get(m, float('nan')):>8.3f}{KP.get(m, float('nan')):>9.3f}{j:>8.4f}")
    say()
    say(f"S_max = {s_max:.4f} ({s_arg})")
    say()

    # ------------------------------------------------------------ pareto front
    say("-" * 78)
    say("3. THE PARETO FRONT (maximise S, minimise N), registered set, width 1")
    say("-" * 78)
    front = []
    for m in treat:
        dominated = any(
            (S[o] >= S[m] and N[o] <= N[m]) and (S[o] > S[m] or N[o] < N[m])
            for o in treat
        )
        if not dominated:
            front.append(m)
    for m in sorted(front, key=lambda m: N[m]):
        say(f"    {m:<26} N = {N[m]:.4f}x   S = {S[m]:.4f}   "
            f"S/Smax = {S[m]/s_max:.3f}   phi = {PHI.get(m, float('nan')):.4f}")
    say()

    # ------------------------------------------------------- the decision rule
    say("-" * 78)
    say("4. THE REGISTERED DECISION RULE")
    say("-" * 78)
    A = [m for m in treat if N[m] <= N_FREE]
    say(f"A = {{ operators with N <= {N_FREE} }} : {len(A)} of {len(treat)}")
    for m in sorted(A, key=lambda m: -S[m]):
        say(f"    {m:<26} N = {N[m]:.4f}x   S = {S[m]:.4f}   S/Smax = {S[m]/s_max:.3f}")
    if A:
        best_a = max(A, key=lambda m: S[m])
        frac = S[best_a] / s_max
        say(f"best member of A: {best_a}  at S/Smax = {frac:.3f}")
        if frac >= S_NEAR_BEST:
            outcome = "O1"
        elif frac >= S_MATERIAL:
            outcome = "O2"
        else:
            outcome = "O3"
    else:
        outcome = "O4"
    say(f"=> registered outcome branch: {outcome}")
    say()

    say("J = (1 - S/Smax) + lambda * max(0, N - 1), lambda sensitivity:")
    for lam in LAMBDA_RANGE:
        best = min(treat, key=lambda m: (1 - S[m] / s_max) + lam * max(0.0, N[m] - 1.0))
        jv = (1 - S[best] / s_max) + lam * max(0.0, N[best] - 1.0)
        tag = "  <- registered" if lam == LAMBDA else ""
        say(f"    lambda = {lam:<5} argmin J = {best:<26} J = {jv:.4f}{tag}")
    say()
    jj = {m: (1 - S[m] / s_max) + LAMBDA * max(0.0, N[m] - 1.0) for m in treat}
    order = sorted(treat, key=lambda m: jj[m])
    say("J ranking at the registered lambda = 1.0 (top 10):")
    for m in order[:10]:
        say(f"    {jj[m]:.4f}  {m}")
    say(f"    ... incumbent {INCUMBENT}: J = {jj[INCUMBENT]:.4f}, "
        f"rank {order.index(INCUMBENT)+1} of {len(order)}")
    say()

    # ------------------------------------------------------------ the O5 test
    say("O5 test -- is the leader inside a tie? (registered: within the measured")
    say("ROI-to-ROI spread on BOTH axes; tie widths come from section 8g)")
    tie_n, tie_s = roi_spread()
    say(f"    measured tie widths: N {tie_n:.4f}   S {tie_s:.4f}")
    lead = order[0]
    tied = [m for m in treat
            if abs(N[m] - N[lead]) <= tie_n and abs(S[m] - S[lead]) <= tie_s]
    say(f"    argmin J = {lead}; tie set has {len(tied)} member(s):")
    for m in sorted(tied, key=lambda m: jj[m]):
        say(f"      {m:<26} N = {N[m]:.4f}  S = {S[m]:.4f}  J = {jj[m]:.4f}  "
            f"params = {nparams(m)}  cost = {COST.get(m, float('nan')):.2f} ms/frame/Mpx")
    if len(tied) > 1:
        say("    => O5 fires. Registered tie-break: (i) fewer parameters, "
            "(ii) lower cost, (iii) the incumbent.")
        fewest = min(nparams(m) for m in tied)
        step_i = [m for m in tied if nparams(m) == fewest]
        say(f"      (i) fewest parameters = {fewest}: {', '.join(sorted(step_i))}")
        if len(step_i) > 1:
            win = min(step_i, key=lambda m: COST.get(m, float("inf")))
            say(f"      (ii) lowest cost: {win} at {COST.get(win, float('nan')):.2f} ms/frame/Mpx")
        else:
            win = step_i[0]
        if INCUMBENT in tied:
            say("      (iii) the incumbent IS in the tie set -- registered rule prefers it")
            win = INCUMBENT
        say(f"    => O5 winner: {win}")
    else:
        say("    => O5 does not fire; the argmin J stands alone.")
    say()

    # ------------------------------------------------- axis agreement (O7 test)
    say("-" * 78)
    say("5. DO THE AXES AGREE? (registered outcome O7 fires below rho = 0.5)")
    say("-" * 78)
    common = [m for m in treat if m in K]
    say(f"    Spearman rho(S, kappa[inject])  = {spearman([S[m] for m in common], [K[m] for m in common]):+.3f}  (n={len(common)})")
    common = [m for m in treat if m in KP]
    say(f"    Spearman rho(S, kappa[G1/G2])   = {spearman([S[m] for m in common], [KP[m] for m in common]):+.3f}  (n={len(common)})")
    common = [m for m in treat if m in PHI and not math.isnan(PHI[m])]
    say(f"    Spearman rho(phi, N)            = {spearman([PHI[m] for m in common], [N[m] for m in common]):+.3f}  (n={len(common)})")
    say(f"    Spearman rho(support_r, N)      = {spearman([meta[m][2] for m in common], [N[m] for m in common]):+.3f}  (n={len(common)})")
    say(f"    Spearman rho(phi, S)            = {spearman([PHI[m] for m in common], [S[m] for m in common]):+.3f}  (n={len(common)})")
    say(f"    Spearman rho(support_r, S)      = {spearman([meta[m][2] for m in common], [S[m] for m in common]):+.3f}  (n={len(common)})")
    say()

    # ---------------------------------------------------- zero-centre-tap verdict
    say("-" * 78)
    say("6. THE ZERO-CENTRE-TAP QUESTION (the milestone's highest-value question)")
    say("-" * 78)
    for m in ["tenengrad-w0-nonorm", "brenner-sym-s2-w0-nonorm", "tenengrad-w0",
              "tenengrad-w2-nonorm", "tenengrad-w2", "tenengrad-w5"]:
        if m in N and m in S:
            say(f"    {m:<26} phi = {PHI.get(m, float('nan')):.4f}   N = {N[m]:.4f}x   "
                f"S = {S[m]:.4f}   S/Smax = {S[m]/s_max:.3f}")
    say()

    # -------------------------------------------------------- the extension set
    if extension:
        say("-" * 78)
        say("7. POST-HOC EXTENSION (amendment A4) -- is the front truncated at w5?")
        say("-" * 78)
        ext = [m for m in extension if m in N and m in S]
        allm = treat + ext
        s_max2 = max(S[m] for m in allm)
        for m in sorted(ext, key=lambda m: -S[m]):
            j = (1.0 - S[m] / s_max2) + LAMBDA * max(0.0, N[m] - 1.0)
            say(f"    {m:<26} phi = {PHI.get(m, float('nan')):.4f}   N = {N[m]:.4f}x   "
                f"S = {S[m]:.4f}   S/Smax = {S[m]/s_max2:.3f}   J = {j:.4f}")
        best2 = min(allm, key=lambda m: (1 - S[m] / s_max2) + LAMBDA * max(0.0, N[m] - 1.0))
        say(f"    argmin J over registered+extension = {best2}")
        say()

    # ---------------------------------------------------------------- sweeps
    # ------------------------------------------------------------ robustness
    say("-" * 78)
    say("9. ROBUSTNESS OF THE RULING -- does the winner survive other aggregations?")
    say("-" * 78)

    def rank_under(nn, ss, label):
        common = [m for m in treat if m in nn and m in ss]
        if not common:
            return
        smx = max(ss[m] for m in common)
        jv = {m: (1 - ss[m] / smx) + LAMBDA * max(0.0, nn[m] - 1.0) for m in common}
        top = sorted(common, key=lambda m: jv[m])[:3]
        say(f"    {label:<44} " + ", ".join(f"{m} ({jv[m]:.3f})" for m in top))

    for st in STACKS:
        nn = {m: median(noise_by_measure(f"noise-{st}.csv")[m])
              for m in treat if m in noise_by_measure(f"noise-{st}.csv")}
        p = planted_by_measure(f"planted-{st}-p1.csv")
        ss = {m: median(p[m]) for m in treat if m in p}
        rank_under(nn, ss, f"{st} alone")
    rank_under(Ncorr, S, "structure-corrected noise axis (Ncorr)")
    for tag in ("tilt4", "tilt16", "tilt32"):
        p = planted_by_measure(f"planted-109MSDCF-{tag}.csv")
        if p:
            rank_under(N, {m: median(p[m]) for m in treat if m in p},
                       f"selectivity measured under {tag}")
    for w in ("9", "17"):
        p = planted_by_measure("planted-109MSDCF-p1.csv", width=w)
        d = noise_by_measure("noise-109MSDCF.csv", width=w)
        if p and d:
            rank_under({m: median(d[m]) for m in treat if m in d},
                       {m: median(p[m]) for m in treat if m in p},
                       f"both axes at regulariser width {w}")
    say()

    say("-" * 78)

    say("8. SWEEPS")
    say("8a. tilt -- does a wider regulariser still help when depth VARIES?")
    say("    tiltK = K frames of depth change across the 256 px ROI (0 = fronto-parallel)")
    for tag in ("tilt0", "tilt4", "tilt16", "tilt32"):
        fn = f"planted-109MSDCF-{tag}.csv"
        if not load(fn):
            continue
        say(f"    {tag}:")
        for m in ["ring-1-3", "tenengrad-w5", "stensor-w5", "brenner-sym-s2-w5",
                  "tenengrad-w0-nonorm", "sml-w5"]:
            cells = []
            for w in ("1", "5", "9", "17", "33"):
                d = planted_by_measure(fn, width=w)
                cells.append(f"w{w}={median(d[m]):.3f}" if m in d else f"w{w}=-")
            say(f"      {m:<26} " + "  ".join(cells))
    say()

    say("8b. ladder steepness alpha (px of blur per frame) -- depth discrimination")
    fn = "planted-109MSDCF-alpha.csv"
    alphas = sorted({r["alpha"] for r in load(fn)}, key=float)
    for m in ["ring-1-3", "tenengrad-w5", "stensor-w5", "brenner-sym-s2-w5",
              "tenengrad-w0-nonorm", "sml-w5", "ctl-random"]:
        cells = []
        for al in alphas:
            d = planted_by_measure(fn, alpha=al)
            cells.append(f"a{al}={median(d[m]):.3f}" if m in d else f"a{al}=-")
        say(f"    {m:<26} " + "  ".join(cells))
    say()

    say("8c. injected-noise scale")
    fn = "planted-109MSDCF-noisescale.csv"
    scales = sorted({r["noise_scale"] for r in load(fn)}, key=float)
    for m in ["ring-1-3", "tenengrad-w5", "stensor-w5", "brenner-sym-s2-w5",
              "tenengrad-w0-nonorm", "sml-w5"]:
        cells = []
        for sc in scales:
            d = planted_by_measure(fn, noise_scale=sc)
            cells.append(f"x{sc}={median(d[m]):.3f}" if m in d else f"x{sc}=-")
        say(f"    {m:<26} " + "  ".join(cells))
    say()

    say("8d. regulariser width on the fronto-parallel P1 plant (S) and the flat ROI (N)")
    for w in ("1", "9", "17"):
        dn = noise_by_measure("noise-109MSDCF.csv", width=w)
        dsel = planted_by_measure("planted-109MSDCF-p1.csv", width=w)
        line = []
        for m in ["ring-1-3", "tenengrad-w5", "stensor-w5"]:
            if m in dn and m in dsel:
                line.append(f"{m}: N={median(dn[m]):.3f} S={median(dsel[m]):.3f}")
        say(f"    width {w:>2}  " + "   ".join(line))
    say()

    say("8e. realised per-frame noise of the planted ladder (registered ceiling: 10% spread)")
    say("    hp_sd on a DETAIL ROI is dominated by scene structure, not noise, and the plant")
    say("    blurs that structure by design -- so the detail figure is not a noise diagnostic.")
    say("    The flat ROI is the honest read of the realised per-frame noise.")
    for st in STACKS:
        rows = load(f"planted-{st}-p1-frames.csv")
        for kind in ("detail", "flat"):
            by = {}
            for r in rows:
                if r["roi_kind"] != kind:
                    continue
                by.setdefault((r["roi"], r["w_true"]), []).append(float(r["hp_sd"]))
            spreads = [(max(v) - min(v)) / mean(v) for v in by.values() if v]
            if spreads:
                gate = ""
                if kind == "flat":
                    gate = "  PASS" if median(spreads) <= 0.10 else "  FAIL"
                say(f"    {st}  {kind:<6} median relative spread of hp_sd across the ladder = "
                    f"{median(spreads)*100:.1f}%   max = {max(spreads)*100:.1f}%{gate}")
    say()

    say("8f. cost, single-threaded")
    cost = {}
    for r in load("cost-109MSDCF.csv"):
        cost[r["measure"]] = float(r["ms_per_frame_mpx"])
    for m in sorted(cost, key=lambda m: cost[m])[:5]:
        say(f"    cheapest  {m:<26} {cost[m]:.3f} ms/frame/Mpx")
    for m in sorted(cost, key=lambda m: -cost[m])[:5]:
        say(f"    dearest   {m:<26} {cost[m]:.3f} ms/frame/Mpx")
    for m in ["ring-1-3", "tenengrad-w5", "stensor-w5", "brenner-sym-s2-w5"]:
        if m in cost:
            say(f"    candidate {m:<26} {cost[m]:.3f} ms/frame/Mpx")
    say()

    say("8g. ROI-to-ROI spread, which sets the tie width for outcome O5")
    for st in STACKS:
        d = noise_by_measure(f"noise-{st}.csv")
        sp = [(max(v) - min(v)) for m, v in d.items() if meta.get(m, ("", "", 0))[1] == "treatment"]
        p = planted_by_measure(f"planted-{st}-p1.csv")
        sp2 = [(max(v) - min(v)) for m, v in p.items() if meta.get(m, ("", "", 0))[1] == "treatment"]
        say(f"    {st}  median range of N across ROIs = {median(sp):.4f}   "
            f"median range of S across (ROI x w_true) = {median(sp2):.4f}")
    say()

    if len(sys.argv) > 2 and sys.argv[1] == "--out":
        with open(sys.argv[2], "w", encoding="utf-8") as fh:
            fh.write("\n".join(OUT) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
