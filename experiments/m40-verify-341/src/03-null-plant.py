"""M40 verification, script 03 -- the TRUE NULL: a detail-free plant, and what the
corrected detail metric actually reads on it.

Question 101 asks what a strictly detail-free region should read under the corrected
detail metric.  Fact 430 assumes 1.0x and calls the measured 0.885x an overshoot.  The
real ROI cannot answer that, because its single-frame corrected reading is 14.7270 DN,
not 0.  So build a region that is detail-free BY CONSTRUCTION and read the answer off.

THE PLANT.  N frames of a constant plane at level L, with independent Gaussian noise per
photosite drawn from the project's own calibrated model (noise.rs:
sigma^2(S) = g*S + (RN_e*g)^2, g = iso/436.8, RN_e = 4.20).  G1 and G2 are drawn
separately, exactly as two photosites, so the green luma carries sigma/sqrt(2).  Then the
SHIPPED pipeline runs on it unchanged: sigma-normalised Tenengrad under a 27x27 box, a
17x17 regulariser, argmax, and the gate.

WHAT THE PLANT CAN AND CANNOT SHOW (AGENTS.md rule 13).  A pure-noise plant has NO focus
signal, so the argmax is driven 100% by noise.  That is the MAXIMAL winner's curse, so
every inflation measured here is an UPPER BOUND on the inflation of a real stack, where
the focus peak is partly deterministic and the selector is partly right for signal
reasons.  A plant that could not express the failure would be one where selection is
forced to be noise-free; this one is the opposite extreme, which is the useful one for
bounding a penalty from above.

WHAT IT MEASURES.
  I_pix(n)   sd(merged | n) / (sigma_model / sqrt(n))     -- the C1 quantity
  I_grad     raw_rms(merged) / noise_rms_model(n = 1)     -- the DETAIL METRIC quantity,
             i.e. exactly the constant that makes sqrt(raw^2 - (I*noise)^2) read ZERO on
             a region with zero detail.  This is the number SELECTION_INFLATION would
             have to be for fact 428's correction to be exact in its own consumer.
  corrected  what the shipped metric prints on a true null, at inflation 1.000 and 1.074.

PRE-REGISTERED (rule 20).  Inputs that would make this fail: if selection cost nothing,
I_pix and I_grad both land at 1.000 and the repair is unnecessary.  If the shipped 1.074
is right for this consumer, I_grad lands at 1.074.  If the step function is right,
I_pix(n) = 1.000 for every n >= 2.  All three are distinguishable outcomes.

Outputs: out/03-null-plant.txt, out/03-null-plant.json
"""

import json
import sys

import numpy as np

BLACK = 512.0
GAIN_DIV = 436.8
RN_E_LOW = 4.20
SIGMA_EPS = 1e-3
WINDOW_RADIUS, REG_RADIUS = 13, 8
FOCUS_NOISE_SD = 0.015214
MARGIN = 48
SIDE = 256
GATES = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0]
SEEDS = list(range(10))

CONFIGS = {
    # level and frame count matched to the two stacks measured in scripts 01/02
    "109-like L=2021 iso160 N=22": dict(level=2020.79, iso=160.0, frames=22),
    "119-like L=4477 iso50 N=33": dict(level=4476.94, iso=50.0, frames=33),
}


def sigma_luma(S, g, read_dn):
    return np.sqrt(0.5 * (g * np.maximum(S, 0.0) + read_dn * read_dn))


def box_mean(a, r):
    H, W = a.shape
    c = np.pad(np.cumsum(np.cumsum(a, 0), 1), ((1, 0), (1, 0)))
    y0 = np.maximum(np.arange(H) - r, 0)
    y1 = np.minimum(np.arange(H) + r, H - 1)
    x0 = np.maximum(np.arange(W) - r, 0)
    x1 = np.minimum(np.arange(W) + r, W - 1)
    s = (
        c[np.ix_(y1 + 1, x1 + 1)]
        - c[np.ix_(y0, x1 + 1)]
        - c[np.ix_(y1 + 1, x0)]
        + c[np.ix_(y0, x0)]
    )
    return s / np.outer(y1 - y0 + 1, x1 - x0 + 1)


def sobel_mag(a):
    p = np.pad(a, 1, mode="edge")
    gx = (
        p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]
        - p[:-2, :-2] - 2 * p[1:-1, :-2] - p[2:, :-2]
    ) * 0.125
    gy = (
        p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]
        - p[:-2, :-2] - 2 * p[:-2, 1:-1] - p[:-2, 2:]
    ) * 0.125
    return np.hypot(gx, gy)


def raw_rms(v):
    dx = v[:-1, 1:] - v[:-1, :-1]
    dy = v[1:, :-1] - v[:-1, :-1]
    return float(np.sqrt((dx * dx + dy * dy).mean()))


def noise_rms(sig):
    s2 = sig**2
    return float(np.sqrt((2 * s2[:-1, :-1] + s2[:-1, 1:] + s2[1:, :-1]).mean()))


def one_trial(level, iso, nframes, seed):
    g = iso / GAIN_DIV
    read_dn = RN_E_LOW * g
    sd_plane = np.sqrt(g * level + read_dn * read_dn)
    side = SIDE + 2 * MARGIN
    rng = np.random.default_rng(seed)
    g1 = BLACK + level + sd_plane * rng.standard_normal((nframes, side, side))
    g2 = BLACK + level + sd_plane * rng.standard_normal((nframes, side, side))
    L = 0.5 * (g1 + g2) - BLACK

    reg = np.empty((nframes, side, side))
    for k in range(nframes):
        luma_f = 0.5 * (np.maximum(g1[k] - BLACK, 0.0) + np.maximum(g2[k] - BLACK, 0.0))
        focus = box_mean(sobel_mag(luma_f), WINDOW_RADIUS) / np.maximum(
            sigma_luma(luma_f, g, read_dn), SIGMA_EPS
        )
        reg[k] = box_mean(focus, REG_RADIUS)

    sl = (slice(MARGIN, MARGIN + SIDE), slice(MARGIN, MARGIN + SIDE))
    reg_r = reg[:, sl[0], sl[1]]
    L_r = L[:, sl[0], sl[1]]
    g1_r, g2_r = g1[:, sl[0], sl[1]], g2[:, sl[0], sl[1]]
    best = reg_r.max(axis=0)
    win = reg_r.argmax(axis=0)

    sigma_model_1 = float(sigma_luma(np.array(level), g, read_dn))
    middle = nframes // 2
    single = L_r[middle]
    sig1 = np.full_like(single, sigma_model_1)
    out = dict(
        sigma_model_1=sigma_model_1,
        single=dict(
            sd=float(single.std(ddof=0)),
            raw_rms=raw_rms(single),
            noise_rms=noise_rms(sig1),
        ),
        gates={},
    )
    out["single"]["I_pix"] = out["single"]["sd"] / sigma_model_1
    out["single"]["I_grad"] = out["single"]["raw_rms"] / out["single"]["noise_rms"]

    for gate in GATES:
        tol = gate * np.sqrt(2.0) * FOCUS_NOISE_SD
        admit = best[None] - reg_r <= tol
        admit[win, np.arange(SIDE)[:, None], np.arange(SIDE)[None, :]] = True
        n = admit.sum(axis=0)
        merged = 0.5 * (
            (g1_r * admit).sum(axis=0) / n + (g2_r * admit).sum(axis=0) / n
        ) - BLACK
        sig_n1 = sigma_model_1 / np.sqrt(n)
        r = raw_rms(merged)
        nr = noise_rms(sig_n1)
        row = dict(
            mean_n=float(n.mean()),
            frac_n1=float((n == 1).mean()),
            sd=float(merged.std(ddof=0)),
            raw_rms=r,
            noise_rms_infl1=nr,
            I_grad=r / nr,
            corrected_infl1=float(np.sqrt(max(0.0, r * r - nr * nr))),
        )
        nr74 = noise_rms(sig_n1 * np.where(n <= 1, 1.074, 1.0))
        row["noise_rms_infl1074"] = nr74
        row["corrected_infl1074"] = -float(np.sqrt(abs(r * r - nr74 * nr74))) if r * r < nr74 * nr74 else float(np.sqrt(r * r - nr74 * nr74))
        # per-n stratification of the PIXEL-domain inflation
        strat = {}
        for nn in range(1, min(9, n.max() + 1)):
            m = n == nn
            if m.sum() < 400:
                continue
            obs = float(merged[m].std(ddof=0))
            pred = sigma_model_1 / np.sqrt(nn)
            strat[int(nn)] = dict(px=int(m.sum()), obs_sd=obs, pred_sd=pred, I=obs / pred)
        row["by_n"] = strat
        # aggregate pixel-domain inflation against the sqrt(n) model
        pred_all = float(np.sqrt((sig_n1**2).mean()))
        row["I_pix_agg"] = float(merged.std(ddof=0)) / pred_all
        out["gates"][gate] = row
    return out


def main():
    out = open("out/03-null-plant.txt", "w", encoding="utf-8")

    def emit(s=""):
        print(s, flush=True)
        out.write(s + "\n")

    emit("=" * 104)
    emit("M40 script 03 -- a detail-free plant under the shipped selector")
    emit("=" * 104)
    emit(f"{len(SEEDS)} seeds per configuration; {SIDE}x{SIDE} evaluated, {MARGIN} px margin")
    emit("The true detail of this plant is EXACTLY ZERO, by construction.")
    emit("")
    allres = {}
    for name, cfg in CONFIGS.items():
        trials = [one_trial(cfg["level"], cfg["iso"], cfg["frames"], s) for s in SEEDS]
        emit(f"### {name}")
        s0 = trials[0]
        emit(f"    model sigma for one green luma sample: {s0['sigma_model_1']:.4f} DN")
        sd = np.array([t["single"]["sd"] for t in trials])
        ig = np.array([t["single"]["I_grad"] for t in trials])
        emit(
            f"    ONE FRAME (no selection): spatial sd {sd.mean():.4f} DN "
            f"= {sd.mean() / s0['sigma_model_1']:.4f}x model     "
            f"raw_rms/noise_rms {ig.mean():.5f} +- {ig.std(ddof=1):.5f}"
        )
        emit("      -> this row is the control: with no selection both must read 1.000x")
        emit("")
        emit(
            "      gate  mean n   n=1 %   I_pix(agg)      I_grad     corrected@1.000   "
            "corrected@1.074"
        )
        rows = {}
        for gate in GATES:
            ip = np.array([t["gates"][gate]["I_pix_agg"] for t in trials])
            ig = np.array([t["gates"][gate]["I_grad"] for t in trials])
            c1 = np.array([t["gates"][gate]["corrected_infl1"] for t in trials])
            c74 = np.array([t["gates"][gate]["corrected_infl1074"] for t in trials])
            mn = np.mean([t["gates"][gate]["mean_n"] for t in trials])
            f1 = np.mean([t["gates"][gate]["frac_n1"] for t in trials])
            emit(
                f"      {gate:4.2f}  {mn:6.3f}  {100 * f1:5.1f}%   "
                f"{ip.mean():.4f}x     {ig.mean():.5f}x   {c1.mean():10.4f} DN   "
                f"{c74.mean():10.4f} DN"
            )
            rows[gate] = dict(
                I_pix=float(ip.mean()),
                I_pix_sd=float(ip.std(ddof=1)),
                I_grad=float(ig.mean()),
                I_grad_sd=float(ig.std(ddof=1)),
                corrected_1=float(c1.mean()),
                corrected_1074=float(c74.mean()),
                mean_n=float(mn),
                frac_n1=float(f1),
            )
        emit("      (corrected@1.074 is signed: negative means the correction over-subtracts,")
        emit("       which the shipped code would clamp to 0 via max(0, .))")
        emit("")
        emit("      per-n pixel-domain inflation I_pix(n) = sd(merged | n) / (sigma/sqrt(n))")
        emit("        gate   " + "".join(f"{f'n={i}':>12s}" for i in range(1, 9)))
        byn = {}
        for gate in GATES:
            cells = []
            for nn in range(1, 9):
                vals = [
                    t["gates"][gate]["by_n"][nn]["I"]
                    for t in trials
                    if nn in t["gates"][gate]["by_n"]
                ]
                if vals:
                    cells.append(f"{np.mean(vals):11.4f}x")
                    byn.setdefault(gate, {})[nn] = float(np.mean(vals))
                else:
                    cells.append(f"{'-':>12s}")
            emit(f"        {gate:4.2f}   " + "".join(cells))
            rows[gate]["by_n"] = byn.get(gate, {})
        emit("")
        allres[name] = rows
    json.dump(allres, open("out/03-null-plant.json", "w"), indent=1)
    out.close()


if __name__ == "__main__":
    sys.exit(main())
