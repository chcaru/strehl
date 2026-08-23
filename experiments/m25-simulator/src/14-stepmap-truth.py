"""14 -- what does the ground truth say about M21's depth-step detector?

`13-coc-probe.py` established that the simulator now reproduces M21's *base
rate* of multi-peakedness (6.6 % at coc 1.0 against a real 4.8 %) but not its
*enrichment* (1.03x against 4.38x), and that the defocus rate is not the cause.

This is the first question in this project that has a ground-truth answer.
M21 cannot know which real pixels sit at a true depth discontinuity, so it
*estimates* them from the R=13 argmax, median-filtered 5x5.  The simulator
knows.  So ask two things the real corpus cannot answer:

  1. **How good is M21's estimated step map?**  Precision and recall against
     the true depth step.
  2. **What enrichment would M21 have measured with a perfect step map?**  If
     the ideal-truth enrichment is large and the estimated one is 1.0x, the
     veiling physics IS reproduced and M21's detector is the limiting factor
     on synthetic data.  If the ideal-truth enrichment is also ~1.0x, the
     simulator genuinely does not reproduce the effect.

Only the second question decides Gate 1c's failure axis, and it is only
askable because a simulator exists.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/14-stepmap-truth.py
"""

from __future__ import annotations

import glob as glob_mod
import os
import sys
import time

import numpy as np
from scipy.ndimage import median_filter, sobel, uniform_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import build as B                                # noqa: E402
from strehl_sim import config as C                               # noqa: E402
from strehl_sim import focus as F                                # noqa: E402
from strehl_sim import scene as SC                               # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402
from strehl_sim.config import Breathing, Capture, Optics         # noqa: E402
from strehl_sim.render import RenderConfig, render_stack         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "stepmap-truth.txt")
REAL = r"C:\dev\macro\test\coffee-bean"
CROP = (600, 1624, 900, 1924)
CFA, SUPERSAMPLE, MARGIN, SUB, K = 2048, 2, 40, 5, 21
NEAR, FAR = 4.0, 16.0
COCS = (1.0, 3.0)
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def ff(g, R):
    """M21's focus field, copied verbatim from its committed script."""
    gx = sobel(g, axis=1, mode="reflect") / 8.0
    gy = sobel(g, axis=0, mode="reflect") / 8.0
    return uniform_filter(np.sqrt(gx * gx + gy * gy), 2 * R + 1)


def multipeak(V, thr=0.04):
    """M21's multi-peak detector, copied verbatim from its committed script."""
    Vs = np.copy(V)
    Vs[1:-1] = (V[:-2] + 2 * V[1:-1] + V[2:]) / 4.0
    mx = Vs.max(0)
    mn = Vs.min(0)
    rng = np.maximum(mx - mn, 1e-6)
    ispk = np.zeros_like(Vs, bool)
    ispk[1:-1] = ((Vs[1:-1] > Vs[:-2] + thr * rng)
                  & (Vs[1:-1] > Vs[2:] + thr * rng))
    return ispk.sum(0) >= 2, (mx - mn) / np.maximum(mx, 1e-6), np.argmax(Vs, 0)


def cfg_coffee(coc, depth_bands=1, margin_px=MARGIN, n=K):
    return RenderConfig(
        sensor=C.A7C2,
        optics=Optics(n_marked=11.0, magnification=2.0, pupil_ratio=1.0),
        capture=Capture(iso=50.0, n_frames=n, coc_px_per_frame=coc),
        breathing=Breathing(total_scale_change=-0.04575,
                            centre_x_px=-22.0, centre_y_px=-113.0),
        margin_px=margin_px, seed=1, channels="green",
        depth_bands=depth_bands)


def main():
    t0 = time.time()
    say("Ground truth vs M21's estimated depth-step map")
    say("the simulator knows which pixels sit at a depth discontinuity; "
        "M21 has to estimate it")
    say()

    fs = sorted(glob_mod.glob(os.path.join(REAL, "*.ARW")))[::SUB]
    import rawpy
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
    tf, tp, nvp, clamped = B.target_psd(mid, iso)
    freq, amp, hist = B.calibrate_psd(cfg_coffee(1.0, margin_px=24),
                                      (512, 512), base_e, ce, beta, 101,
                                      tf, tp, float(peak), iters=4)
    psd = (freq, amp)
    say(f"real: ISO {iso:.0f}, mean {mid.mean():.0f} DN, sd {mid.std():.0f} DN,"
        f" beta {beta:.3f}, peak frame {peak}")
    say("PSD shaping mismatch by iteration: "
        + ", ".join(f"{h:.4f}" for h in hist))
    say()

    gain = lv / lv[len(G) // 2]
    rows = []
    for coc in COCS:
        tr = time.time()
        sc = SC.two_layer_occlusion(
            (CFA, CFA), SUPERSAMPLE, base_e, ce, base_e * 1.25, ce * 1.25,
            FAR, NEAR, shape="discs", edge_frac=0.35, beta=beta, seed=7,
            margin=MARGIN, psd=psd)
        st = render_stack(sc, cfg_coffee(coc), gain_series=gain)
        Gs = (st.frames[:, 0::2, 1::2].astype(np.float32) - 512)
        say(f"--- coc {coc} px/frame  (render {time.time() - tr:.0f}s, "
            f"green {Gs.shape[1]}x{Gs.shape[2]}) ---")

        # ---- M21's own pipeline, verbatim ----------------------------
        V2 = np.stack([ff(g, 2) for g in Gs])
        V13 = np.stack([ff(g, 13) for g in Gs])
        _, c13, am13 = multipeak(V13)
        amr = median_filter(am13.astype(np.float32), 5)
        step = np.abs(np.gradient(amr)[0]) + np.abs(np.gradient(amr)[1])
        strong = c13 > 0.10
        mp, _, _ = multipeak(V2)

        # ---- the truth, which no real capture can supply -------------
        vf = st.truth["visible_focus"][0::2, 1::2]
        af = st.truth["alpha_front"][0::2, 1::2]
        tstep = (np.abs(np.gradient(vf)[0])
                 + np.abs(np.gradient(vf)[1])) >= 1.0
        tpartial = (af > 0.02) & (af < 0.98)

        est_hi = strong & (step >= 1.0)
        est_lo = strong & (step < 0.25)
        tru_hi = strong & tstep
        tru_lo = strong & ~tstep & ~tpartial

        inter = float((est_hi & tru_hi).sum())
        prec = inter / max(est_hi.sum(), 1)
        rec = inter / max(tru_hi.sum(), 1)
        say(f"  M21 estimated step map: {int(est_hi.sum()):>7} px flagged; "
            f"TRUE step map: {int(tru_hi.sum()):>7} px")
        say(f"  precision {100 * prec:5.1f}%   recall {100 * rec:5.1f}%   "
            f"(over-flagging factor "
            f"{est_hi.sum() / max(tru_hi.sum(), 1):.2f}x)")

        def enr(hi, lo):
            if hi.sum() < 500 or lo.sum() < 500:
                return float("nan"), float("nan"), float("nan")
            a = mp[hi].mean() * 100
            b = mp[lo].mean() * 100
            return a, b, a / max(b, 1e-9)

        ea, eb, ee = enr(est_hi, est_lo)
        ta, tb, te = enr(tru_hi, tru_lo)
        pa, pb, pe = enr(strong & tpartial, tru_lo)
        say(f"  ESTIMATED step map : {ea:5.1f}% at steps vs {eb:5.1f}% "
            f"smooth = {ee:5.2f}x")
        say(f"  TRUE      step map : {ta:5.1f}% at steps vs {tb:5.1f}% "
            f"smooth = {te:5.2f}x")
        say(f"  TRUE partial-alpha : {pa:5.1f}% veiled  vs {pb:5.1f}% "
            f"smooth = {pe:5.2f}x   <- the pixels M21's thesis is about")
        say(f"  overall multi-peak on strong pixels: "
            f"{mp[strong].mean() * 100:.1f}%  (real coffee-bean 4.8%)")
        say()
        rows.append((coc, ee, te, pe))

    say("=" * 74)
    say(f"{'coc':>5} {'M21 estimated':>14} {'true step map':>14} "
        f"{'true veiled px':>15}")
    for coc, ee, te, pe in rows:
        say(f"{coc:>5} {ee:>13.2f}x {te:>13.2f}x {pe:>14.2f}x")
    say(f"{'REAL (M21)':>5} {4.38:>13.2f}x {'--':>14} {'--':>15}")
    say()
    best_true = max(r[3] for r in rows)
    if best_true >= 2.0:
        say("VERDICT: the veiling effect IS present in the simulated stacks "
            "-- it is visible when the depth-step population is taken from "
            "ground truth and invisible when it is estimated the way M21 "
            "estimates it.  Gate 1c's failure is then a statement about the "
            "detector on this plant, not about the forward model.")
    else:
        say("VERDICT: the veiling effect is NOT recoverable even with a "
            "perfect depth-step map.  The forward model does not reproduce "
            "M21's enrichment on this plant, and that is an honest failure "
            "axis of the simulator.")
    say(f"[{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
