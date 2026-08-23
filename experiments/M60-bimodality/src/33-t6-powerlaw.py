"""33 -- T6: is fact 603's 4.5x a plant effect or denominator relief?

PRE-REGISTERED in PREREGISTRATION-B.md section 7b, committed a2d8756 BEFORE the
discs-powerlaw variant was rendered or scored.

Fact 603 records multi-scale occluder geometry moving truth-gated enrichment from
0.19x to 0.86x, "the largest single effect ever measured on this statistic".
T2 showed S0's threshold denominator is 3.942x inflated at veiled pixels in the
single-scale control.  Multi-scale geometry replaces one high-contrast boundary
with many small ones, lowering the range S0 divides by -- so the same
manipulation predicts the same improvement with no extra veiling at all.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/M60-bimodality/src/33-t6-powerlaw.py
"""

from __future__ import annotations

import glob as glob_mod
import json
import os
import sys
import time

import numpy as np
from scipy.ndimage import sobel, uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.abspath(os.path.join(HERE, "..", "..", "m25-simulator", "src"))
sys.path.insert(0, HERE)
sys.path.insert(0, SIM)
import m60lib as L                                               # noqa: E402
from strehl_sim import build as B                                # noqa: E402
from strehl_sim import config as C                               # noqa: E402
from strehl_sim import focus as F                                # noqa: E402
from strehl_sim import scene as SC                               # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402
from strehl_sim.config import Breathing, Capture, Optics         # noqa: E402
from strehl_sim.render import RenderConfig, render_stack         # noqa: E402

DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT = os.path.join(DATA, "33-t6.txt")
OUTJ = os.path.join(DATA, "33-t6.json")

REAL = r"C:\dev\macro\test\coffee-bean"
CROP = (600, 1624, 900, 1924)
CFA, SUPERSAMPLE, MARGIN, SUB, K = 2048, 2, 40, 5, 21
NEAR, FAR, COC = 4.0, 16.0, 1.0
MC_REPS, FPR, MIN_BIN = 16, 0.01, 500
SEED = 20260825

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def ff(g, R):
    gx = sobel(g, axis=1, mode='reflect') / 8.0
    gy = sobel(g, axis=0, mode='reflect') / 8.0
    return uniform_filter(np.sqrt(gx * gx + gy * gy), 2 * R + 1)


def multipeak(V, thr=0.04):
    Vs = np.copy(V)
    Vs[1:-1] = (V[:-2] + 2 * V[1:-1] + V[2:]) / 4.0
    mx, mn = Vs.max(0), Vs.min(0)
    rng = np.maximum(mx - mn, 1e-6)
    ispk = np.zeros_like(Vs, bool)
    ispk[1:-1] = (Vs[1:-1] > Vs[:-2] + thr * rng) & (Vs[1:-1] > Vs[2:] + thr * rng)
    return ispk.sum(0) >= 2, (mx - mn) / np.maximum(mx, 1e-6), np.argmax(Vs, 0)


def enrich(mp, hi, lo):
    if hi.sum() < MIN_BIN or lo.sum() < MIN_BIN:
        return float("nan"), float("nan"), float("nan")
    a, b = mp[hi].mean() * 100.0, mp[lo].mean() * 100.0
    return a, b, a / max(b, 1e-9)


def cfg(coc, margin_px=MARGIN, n=K):
    return RenderConfig(
        sensor=C.A7C2,
        optics=Optics(n_marked=11.0, magnification=2.0, pupil_ratio=1.0),
        capture=Capture(iso=50.0, n_frames=n, coc_px_per_frame=coc),
        breathing=Breathing(total_scale_change=-0.04575,
                            centre_x_px=-22.0, centre_y_px=-113.0),
        margin_px=margin_px, seed=1, channels="green", depth_bands=1)


def score(Gs, vf, af, iso, rng0, label):
    n = Gs.shape[0]
    V2 = np.stack([ff(Gs[k], 2) for k in range(n)])
    V13 = np.stack([ff(Gs[k], 13) for k in range(n)])
    _, c13, _ = multipeak(V13)
    strong = c13 > 0.10
    tstep = (np.abs(np.gradient(vf)[0]) + np.abs(np.gradient(vf)[1])) >= 1.0
    tpartial = (af > 0.02) & (af < 0.98)
    veiled, smooth = strong & tpartial, strong & ~tstep & ~tpartial

    say(f"  power: veiled {int(veiled.sum())}  smooth {int(smooth.sum())}  "
        f"strong {strong.mean()*100:.1f}%")
    assert min(veiled.sum(), smooth.sum()) >= MIN_BIN, "below M25's floor"

    mp0, _, _ = multipeak(V2)
    a0, b0, e0 = enrich(mp0, veiled, smooth)

    Vs = np.copy(V2)
    Vs[1:-1] = (V2[:-2] + 2 * V2[1:-1] + V2[2:]) / 4.0
    rngmap = Vs.max(0) - Vs.min(0)
    rv, rs = float(np.median(rngmap[veiled])), float(np.median(rngmap[smooth]))

    Ibar = Gs.mean(0)
    sigf = L.focus_sigma_mc(Ibar, 2, iso, MC_REPS, rng0)
    Sr = np.repeat(sigf[None], n, 0)
    Vnull = np.stack([ff(Ibar + rng0.normal(0, 1, Ibar.shape).astype(np.float32)
                         * L.sigma_dn(Ibar, iso), 2) for _ in range(n)])
    rn = L.second_peak(Vnull)
    zn, _, _, _ = L.prominence_z(Vnull, Sr, rn)
    z2 = float(np.quantile(zn, 1.0 - FPR))
    r2 = L.second_peak(V2)
    zz, prom, den, _ = L.prominence_z(V2, Sr, r2)
    mp2 = zz > z2
    a2, b2, e2 = enrich(mp2, veiled, smooth)

    perm = rng0.permutation(n)
    _, _, p0 = enrich(multipeak(V2[perm])[0], veiled, smooth)
    r2p = L.second_peak(V2[perm])
    zzp, _, _, _ = L.prominence_z(V2[perm], Sr, r2p)
    _, _, p2 = enrich(zzp > z2, veiled, smooth)

    say(f"  S0 (M21 verbatim)  veiled {a0:5.2f}%  smooth {b0:5.2f}%  "
        f"= {e0:5.2f}x   placebo {p0:.2f}  base {mp0[strong].mean()*100:.1f}%")
    say(f"  S2 (M60 prominence) veiled {a2:5.2f}%  smooth {b2:5.2f}%  "
        f"= {e2:5.2f}x   placebo {p2:.2f}  base {mp2[strong].mean()*100:.1f}%")
    say(f"  T2 denominator: rng veiled {rv:8.3f} DN  smooth {rs:8.3f} DN  "
        f"= {rv/max(rs,1e-9):.3f}x")
    say(f"  S2 numerator/denominator (rule 39): prom veiled "
        f"{np.median(prom[veiled]):.3f} smooth {np.median(prom[smooth]):.3f} DN; "
        f"den veiled {np.median(den[veiled]):.3f} smooth "
        f"{np.median(den[smooth]):.3f} DN")
    return dict(label=label, s0=e0, s2=e2, rng_ratio=rv / max(rs, 1e-9),
                rng_veiled=rv, rng_smooth=rs, placebo0=p0, placebo2=p2,
                base0=float(mp0[strong].mean() * 100),
                base2=float(mp2[strong].mean() * 100),
                veiled_px=int(veiled.sum()), smooth_px=int(smooth.sum()))


def main() -> None:
    t0 = time.time()
    rng0 = np.random.default_rng(SEED)
    say("M60b/33 -- T6: fact 603's 4.5x, plant effect or denominator relief?")
    say("PRE-REGISTERED PREREGISTRATION-B.md section 7b, commit a2d8756.")
    say()

    import rawpy
    fs = sorted(glob_mod.glob(os.path.join(REAL, "*.ARW")))[::SUB]
    G = []
    for f in fs:
        with rawpy.imread(f) as rr:
            g = rr.raw_image_visible[0::2, 1::2].astype(np.float32) - 512
        G.append(g[CROP[0]:CROP[1], CROP[2]:CROP[3]])
    G = np.stack(G)
    iso = S.iso_of(REAL)
    nm = F.NoiseModel.for_iso(iso)
    lv = G.mean(axis=(1, 2))
    mid = G[len(G) // 2]
    beta = B.fit_beta(mid)
    nv = 0.5 * (nm.gain_dn_per_e * mid.mean()
                + (nm.read_noise_e * nm.gain_dn_per_e) ** 2)
    struct = float(np.sqrt(max(mid.std() ** 2 - nv, 1.0)))
    base_e = float(mid.mean()) / nm.gain_dn_per_e
    ce = struct / nm.gain_dn_per_e
    m13 = [x for x in F.design(False) if x.name == "ring-1-3"][0]
    fr = np.array([m13.compute(np.maximum(G[k], 0), nm)[16:-16, 16:-16].mean()
                   for k in range(len(G))])
    peak = int(np.argmax(fr))
    B.set_supersample(SUPERSAMPLE)
    tf, tp, _, _ = B.target_psd(mid, iso)
    freq, amp, hist = B.calibrate_psd(cfg(COC, margin_px=24), (512, 512),
                                      base_e, ce, beta, 101, tf, tp,
                                      float(peak), iters=4)
    psd = (freq, amp)
    gain = lv / lv[len(G) // 2]

    rows = []
    for label, kw in (("discs (control, single-scale)", dict(shape="discs")),
                      ("discs-powerlaw r^-3, 2-160px",
                       dict(shape="discs-powerlaw"))):
        tr = time.time()
        sc = SC.two_layer_occlusion(
            (CFA, CFA), SUPERSAMPLE, base_e, ce, base_e * 1.25, ce * 1.25,
            FAR, NEAR, edge_frac=0.35, beta=beta, seed=7,
            margin=MARGIN, psd=psd, **kw)
        al = sc.layers[1].alpha
        gy, gx = np.gradient(al)
        per = float(np.sqrt(gy * gy + gx * gx).sum()) / al.size
        feat = 1.0 / max(per, 1e-9)
        st = render_stack(sc, cfg(COC), gain_series=gain)
        Gs = (st.frames[:, 0::2, 1::2].astype(np.float32) - 512)
        say(f"--- {label} ---")
        say(f"  occluder: coverage {al.mean()*100:.1f}%, mean feature "
            f"~{feat:.1f} latent px ({feat/SUPERSAMPLE:.1f} sensor px), "
            f"render {time.time()-tr:.0f}s")
        r = score(Gs, st.truth["visible_focus"][0::2, 1::2],
                  st.truth["alpha_front"][0::2, 1::2], iso, rng0, label)
        r["feature_latent_px"] = feat
        rows.append(r)
        say()

    c, p = rows[0], rows[1]
    s0r = p["s0"] / max(c["s0"], 1e-9)
    s2r = p["s2"] / max(c["s2"], 1e-9)
    dr = p["rng_ratio"] / max(c["rng_ratio"], 1e-9)
    say("T6 VERDICT by the pre-registered rule (section 7b):")
    say(f"  S0  control {c['s0']:.2f}x -> powerlaw {p['s0']:.2f}x   "
        f"= {s0r:.2f}x improvement   (fact 603 records 0.19 -> 0.86)")
    say(f"  S2  control {c['s2']:.2f}x -> powerlaw {p['s2']:.2f}x   "
        f"= {s2r:.2f}x improvement")
    say(f"  T2 denominator ratio  control {c['rng_ratio']:.3f}x -> "
        f"powerlaw {p['rng_ratio']:.3f}x   = {dr:.2f}x")
    comparable = abs(s2r - s0r) <= 0.30 * max(s0r, 1e-9)
    relief = (p["s0"] > c["s0"]) and (p["rng_ratio"] < c["rng_ratio"]) and not comparable
    if not (0.6 <= p["s0"] / 0.86 <= 1.4):
        v = "NEITHER -- failed to reproduce the 0.86x variant; report and stop"
    elif relief:
        v = ("DENOMINATOR RELIEF -- fact 603's 4.5x is substantially an "
             "instrument effect")
    elif comparable and p["s0"] > c["s0"]:
        v = "REAL VEILING -- fact 603's reading stands"
    else:
        v = "INDETERMINATE against the registered rule"
    say(f"  S2 improvement is {'' if comparable else 'NOT '}comparable to S0's "
        f"(|{s2r:.2f}-{s0r:.2f}| {'<=' if comparable else '>'} "
        f"{0.30*s0r:.2f})")
    say(f"  -> {v}")
    say()
    say(f"total {time.time()-t0:.0f}s")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    with open(OUTJ, "w", encoding="utf-8") as fh:
        json.dump(dict(rows=rows, s0_ratio=s0r, s2_ratio=s2r,
                       denom_ratio=dr, verdict=v), fh, indent=1)


if __name__ == "__main__":
    main()
