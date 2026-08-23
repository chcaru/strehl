"""15 -- does my occluder's luminance step suppress the veiling signature?

`14-stepmap-truth.py` produced the most uncomfortable number in this milestone:
with a **perfect** depth-step map, the truly-veiled pixels of the simulated
occlusion scene are multi-peaked at **1.6 %** against **6.8 %** on smooth
depth -- an enrichment of **0.24x**.  Not a small effect in the wrong
direction: the effect has the wrong *sign*.

The leading hypothesis is a plant-design error, not a physics error.  My
occluder is rendered at `base_e * 1.25` against a background at `base_e`, so
the alpha boundary is also a **25 % luminance step**.  M21's detector is a
Sobel gradient magnitude, so at those pixels the gradient is dominated by the
step, and the step is sharpest exactly when the *foreground* is in focus.  One
dominant peak, not two -- and the veiling signature is buried under a feature I
put there myself.

A real occluding edge on a coffee bean is between two similarly-lit textured
surfaces.  So: render the same scene with the two layers at **identical**
radiometry, change nothing else, and re-measure the truth-gated enrichment.

If the enrichment rises, the failure is mine and the plant is wrong.
If it stays at ~0.25x, the forward model does not reproduce veiling and that
stands as the milestone's failure axis.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/15-lumstep-probe.py
"""

from __future__ import annotations

import glob as glob_mod
import os
import sys
import time

import numpy as np
from scipy.ndimage import sobel, uniform_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import build as B                                # noqa: E402
from strehl_sim import config as C                               # noqa: E402
from strehl_sim import focus as F                                # noqa: E402
from strehl_sim import scene as SC                               # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402
from strehl_sim.config import Breathing, Capture, Optics         # noqa: E402
from strehl_sim.render import RenderConfig, render_stack         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "lumstep-probe.txt")
REAL = r"C:\dev\macro\test\coffee-bean"
CROP = (600, 1624, 900, 1924)
CFA, SUPERSAMPLE, MARGIN, SUB, K = 2048, 2, 40, 5, 21
NEAR, FAR, COC = 4.0, 16.0, 1.0
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def ff(g, R):
    gx = sobel(g, axis=1, mode="reflect") / 8.0
    gy = sobel(g, axis=0, mode="reflect") / 8.0
    return uniform_filter(np.sqrt(gx * gx + gy * gy), 2 * R + 1)


def multipeak(V, thr=0.04):
    Vs = np.copy(V)
    Vs[1:-1] = (V[:-2] + 2 * V[1:-1] + V[2:]) / 4.0
    mx = Vs.max(0)
    mn = Vs.min(0)
    rng = np.maximum(mx - mn, 1e-6)
    ispk = np.zeros_like(Vs, bool)
    ispk[1:-1] = ((Vs[1:-1] > Vs[:-2] + thr * rng)
                  & (Vs[1:-1] > Vs[2:] + thr * rng))
    return ispk.sum(0) >= 2, (mx - mn) / np.maximum(mx, 1e-6), np.argmax(Vs, 0)


def cfg(coc):
    return RenderConfig(
        sensor=C.A7C2,
        optics=Optics(n_marked=11.0, magnification=2.0, pupil_ratio=1.0),
        capture=Capture(iso=50.0, n_frames=K, coc_px_per_frame=coc),
        breathing=Breathing(total_scale_change=-0.04575,
                            centre_x_px=-22.0, centre_y_px=-113.0),
        margin_px=MARGIN, seed=1, channels="green", depth_bands=1)


def main():
    t0 = time.time()
    say("Does the occluder's own luminance step bury the veiling signature?")
    say(f"one variable: foreground radiometry.  coc {COC} px/frame, "
        f"everything else as 14-stepmap-truth.py")
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
    tf, tp, _, _ = B.target_psd(mid, iso)
    freq, amp, _ = B.calibrate_psd(
        RenderConfig(sensor=C.A7C2,
                     optics=Optics(n_marked=11.0, magnification=2.0,
                                   pupil_ratio=1.0),
                     capture=Capture(iso=50.0, n_frames=K,
                                     coc_px_per_frame=1.0),
                     breathing=Breathing(total_scale_change=-0.04575,
                                         centre_x_px=-22.0,
                                         centre_y_px=-113.0),
                     margin_px=24, seed=1, channels="green", depth_bands=1),
        (512, 512), base_e, ce, beta, 101, tf, tp, float(peak), iters=4)
    psd = (freq, amp)
    gain = lv / lv[len(G) // 2]

    variants = {
        "step  (fg 1.25x bg) -- as Gate 1c": (base_e * 1.25, ce * 1.25),
        "matched (fg == bg)  -- the fix":    (base_e, ce),
    }
    rows = []
    for label, (fe, fc) in variants.items():
        tr = time.time()
        sc = SC.two_layer_occlusion(
            (CFA, CFA), SUPERSAMPLE, base_e, ce, fe, fc, FAR, NEAR,
            shape="discs", edge_frac=0.35, beta=beta, seed=7, margin=MARGIN,
            psd=psd)
        st = render_stack(sc, cfg(COC), gain_series=gain)
        Gs = st.frames[:, 0::2, 1::2].astype(np.float32) - 512
        V2 = np.stack([ff(g, 2) for g in Gs])
        V13 = np.stack([ff(g, 13) for g in Gs])
        _, c13, _ = multipeak(V13)
        strong = c13 > 0.10
        mp, _, _ = multipeak(V2)
        vf = st.truth["visible_focus"][0::2, 1::2]
        af = st.truth["alpha_front"][0::2, 1::2]
        tstep = (np.abs(np.gradient(vf)[0])
                 + np.abs(np.gradient(vf)[1])) >= 1.0
        tpart = (af > 0.02) & (af < 0.98)
        hi = strong & tpart
        lo = strong & ~tstep & ~tpart
        a = mp[hi].mean() * 100
        b = mp[lo].mean() * 100
        e = a / max(b, 1e-9)
        # how strong is the luminance step relative to the texture?
        f0 = Gs[int(round(NEAR))]
        gm = np.sqrt((sobel(f0, axis=1) / 8.0) ** 2
                     + (sobel(f0, axis=0) / 8.0) ** 2)
        edge = gm[hi].mean()
        flat = gm[lo].mean()
        say(f"--- {label} (render {time.time() - tr:.0f}s) ---")
        say(f"  truth-gated: {a:5.2f}% multi-peak on veiled px vs "
            f"{b:5.2f}% on smooth = {e:5.2f}x   (n {int(hi.sum())}/"
            f"{int(lo.sum())})")
        say(f"  gradient magnitude at fg-focus frame: veiled {edge:.1f} DN/px "
            f"vs smooth {flat:.1f} DN/px = {edge / max(flat, 1e-9):.2f}x")
        say(f"  overall multi-peak on strong px {mp[strong].mean() * 100:.1f}%"
            f"  (real coffee-bean 4.8%)")
        say()
        rows.append((label, e, edge / max(flat, 1e-9)))

    say("=" * 74)
    say(f"{'variant':<36} {'veiled enrich':>14} {'edge/flat grad':>15}")
    for label, e, r in rows:
        say(f"{label:<36} {e:>13.2f}x {r:>14.2f}x")
    say()
    a0, a1 = rows[0][1], rows[1][1]
    if a1 >= a0 * 1.5:
        say(f"VERDICT: removing the luminance step raises the truth-gated "
            f"enrichment {a0:.2f}x -> {a1:.2f}x.  Gate 1c's plant was "
            f"mis-designed: the occluder's own brightness step dominated the "
            f"Sobel focus response and buried the two-depth signature.  This "
            f"is my error, not the forward model's.")
    else:
        say(f"VERDICT: removing the luminance step does not help "
            f"({a0:.2f}x -> {a1:.2f}x).  The hypothesis is refuted and the "
            f"failure to reproduce M21's enrichment stands as an unexplained "
            f"failure axis of the simulator.")
    say(f"[{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
