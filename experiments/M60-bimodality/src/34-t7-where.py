"""34 -- T7: where does the flagged second peak actually land?

PRE-REGISTERED in PREREGISTRATION-B.md section 7c, committed 20f7e23 BEFORE any
k2-location statistic was computed.

S2 reads 1.23x on M25's control plant where S0 reads 0.19x.  But the veiled
population sits on the occluder boundary, which is a high-contrast edge, and
M60's first pass established that a single depth at a high-contrast edge
generates secondary through-focus peaks by itself.  So 1.23x might not be
veiling either.

The plant knows the answer: background at focus index 16, foreground at 4.

Uses the frames frozen by 30-render-m25-plant.py -- the same arrays T1 and T2
were computed on.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/M60-bimodality/src/34-t7-where.py
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
from scipy.ndimage import sobel, uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m60lib as L                                               # noqa: E402

DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
PLANT = os.path.join(DATA, "30-m25-plant.npz")
OUT = os.path.join(DATA, "34-t7.txt")
OUTJ = os.path.join(DATA, "34-t7.json")

MC_REPS, FPR = 16, 0.01
WIN = 2
SEED = 20260826
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def ff(g, R):
    gx = sobel(g, axis=1, mode='reflect') / 8.0
    gy = sobel(g, axis=0, mode='reflect') / 8.0
    return uniform_filter(np.sqrt(gx * gx + gy * gy), 2 * R + 1)


def multipeak_full(V, thr=0.04):
    """M21's detector, returning the peak mask as well as the flags."""
    Vs = np.copy(V)
    Vs[1:-1] = (V[:-2] + 2 * V[1:-1] + V[2:]) / 4.0
    mx, mn = Vs.max(0), Vs.min(0)
    rng = np.maximum(mx - mn, 1e-6)
    ispk = np.zeros_like(Vs, bool)
    ispk[1:-1] = (Vs[1:-1] > Vs[:-2] + thr * rng) & (Vs[1:-1] > Vs[2:] + thr * rng)
    return ispk.sum(0) >= 2, (mx - mn) / np.maximum(mx, 1e-6), ispk, Vs


def second_peak_of_mask(ispk, Vs, k1):
    """Index of the tallest flagged peak that is not the global max."""
    n = Vs.shape[0]
    idx = np.arange(n)[:, None, None]
    cand = ispk & (idx != k1[None])
    val = np.where(cand, Vs, -np.inf)
    return np.argmax(val, 0), cand.any(0)


def hist_line(k2, sel, n):
    h = np.bincount(k2[sel], minlength=n)
    tot = max(h.sum(), 1)
    return " ".join(f"{100.0*h[i]/tot:4.1f}" for i in range(n))


def main() -> None:
    t0 = time.time()
    rng0 = np.random.default_rng(SEED)
    d = np.load(PLANT)
    G, vf, af = d["frames"], d["visible_focus"], d["alpha_front"]
    iso = float(d["iso"])
    n = G.shape[0]
    K_BG, K_FG = int(float(d["far"])), int(float(d["near"]))

    say("M60b/34 -- T7: where does the flagged second peak land?")
    say("PRE-REGISTERED PREREGISTRATION-B.md section 7c, commit 20f7e23.")
    say(f"plant truth: background focus index {K_BG}, foreground {K_FG}, "
        f"{n} frames, window +/-{WIN}")
    say()

    V2 = np.stack([ff(G[k], 2) for k in range(n)])
    V13 = np.stack([ff(G[k], 13) for k in range(n)])
    _, c13, _, _ = multipeak_full(V13)
    strong = c13 > 0.10
    tstep = (np.abs(np.gradient(vf)[0]) + np.abs(np.gradient(vf)[1])) >= 1.0
    tpartial = (af > 0.02) & (af < 0.98)
    veiled, smooth = strong & tpartial, strong & ~tstep & ~tpartial

    # chance rate over interior indices, stated before any measurement
    interior = n - 2
    win = min(K_BG + WIN, n - 2) - max(K_BG - WIN, 1) + 1
    chance = 100.0 * win / interior
    say(f"POWER: veiled {int(veiled.sum())}  smooth {int(smooth.sum())}")
    say(f"chance rate: {win} of {interior} interior indices = {chance:.1f}%")
    say()

    # --- S2 ---------------------------------------------------------------
    Ibar = G.mean(0)
    sigf = L.focus_sigma_mc(Ibar, 2, iso, MC_REPS, rng0)
    S = np.repeat(sigf[None], n, 0)
    Vnull = np.stack([ff(Ibar + rng0.normal(0, 1, Ibar.shape).astype(np.float32)
                         * L.sigma_dn(Ibar, iso), 2) for _ in range(n)])
    rn = L.second_peak(Vnull)
    zn, _, _, _ = L.prominence_z(Vnull, S, rn)
    z2 = float(np.quantile(zn, 1.0 - FPR))
    r2 = L.second_peak(V2)
    zz, _, _, _ = L.prominence_z(V2, S, r2)
    flag2 = zz > z2
    k2_s2 = r2["k2"]
    k1_s2 = r2["k1"]

    # --- S0 ---------------------------------------------------------------
    f0, _, ispk, Vs = multipeak_full(V2)
    k1_0 = np.argmax(Vs, 0)
    k2_s0, has2 = second_peak_of_mask(ispk, Vs, k1_0)
    flag0 = f0 & has2

    # --- permutation null for S2 ------------------------------------------
    perm = rng0.permutation(n)
    r2p = L.second_peak(V2[perm])
    zzp, _, _, _ = L.prominence_z(V2[perm], S, r2p)
    flag2p, k2p = zzp > z2, r2p["k2"]

    rows = {}
    say(f"{'statistic / population':<38}{'n flagged':>11}"
        f"{'k2 in bg+/-2':>14}{'k1 in fg+/-2':>14}")
    for nm, flag, k2m, k1m in (
        ("S2  veiled  (truth: has background)", flag2 & veiled, k2_s2, k1_s2),
        ("S2  smooth  (truth: no background)", flag2 & smooth, k2_s2, k1_s2),
        ("S2  veiled, frames permuted (null)", flag2p & veiled, k2p, r2p["k1"]),
        ("S0  veiled  (M21 verbatim)", flag0 & veiled, k2_s0, k1_0),
        ("S0  smooth  (M21 verbatim)", flag0 & smooth, k2_s0, k1_0),
    ):
        cnt = int(flag.sum())
        if cnt < 500:
            say(f"{nm:<38}{cnt:>11}     too few, not interpreted")
            rows[nm] = dict(n=cnt, bg=None, fg=None)
            continue
        bg = 100.0 * (np.abs(k2m[flag] - K_BG) <= WIN).mean()
        fg = 100.0 * (np.abs(k1m[flag] - K_FG) <= WIN).mean()
        say(f"{nm:<38}{cnt:>11}{bg:13.1f}%{fg:13.1f}%")
        rows[nm] = dict(n=cnt, bg=float(bg), fg=float(fg))
    say()

    say("full k2 histogram, % of flagged pixels at each frame index")
    say("        " + " ".join(f"{i:4d}" for i in range(n)))
    say(f"{'bg=16':>8} " + " ".join(("  ^ " if i == K_BG else
                                     ("  f " if i == K_FG else "    "))
                                    for i in range(n)))
    for nm, flag, k2m in (("S2 veil", flag2 & veiled, k2_s2),
                          ("S2 smth", flag2 & smooth, k2_s2),
                          ("S0 veil", flag0 & veiled, k2_s0),
                          ("S0 smth", flag0 & smooth, k2_s0)):
        if int(flag.sum()) >= 500:
            say(f"{nm:>8} " + hist_line(k2m, flag, n))
    say()

    # --- verdict ----------------------------------------------------------
    v_bg = rows["S2  veiled  (truth: has background)"]["bg"]
    s_bg = rows["S2  smooth  (truth: no background)"]["bg"]
    say("T7 VERDICT by the pre-registered rule (section 7c):")
    say(f"  S2 flagged-veiled k2 within +/-{WIN} of the true background index: "
        f"{v_bg:.1f}%")
    say(f"  uniform chance {chance:.1f}%  -> {v_bg/chance:.2f}x")
    say(f"  flagged-smooth {s_bg:.1f}%    -> {v_bg/max(s_bg,1e-9):.2f}x")
    if v_bg >= 2.0 * chance and v_bg >= 2.0 * s_bg:
        v = ("VEILING -- S2's enrichment is genuine veiling; the plant contains "
             "the phenomenon and S0 cannot see it")
    elif abs(v_bg - chance) <= 0.30 * chance or v_bg <= 1.15 * s_bg:
        v = ("SIDE-LOBE -- S2's enrichment is not veiling either; the plant's "
             "veiling is undetectable by any statistic tried here")
    else:
        v = "INDETERMINATE against the registered rule"
    say(f"  -> {v}")
    say()
    say(f"total {time.time()-t0:.0f}s")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    with open(OUTJ, "w", encoding="utf-8") as fh:
        json.dump(dict(rows=rows, chance=chance, k_bg=K_BG, k_fg=K_FG,
                       verdict=v), fh, indent=1)


if __name__ == "__main__":
    main()
