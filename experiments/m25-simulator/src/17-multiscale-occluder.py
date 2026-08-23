"""17 -- is multi-scale occluder geometry the missing ingredient?  (question 132)

Section 11 of M25-simulator-measured.md pre-registers this, and the gate below
is the pre-registered one.  Read that section before this script.

Section 4.3 measured the truth-gated veiling enrichment at **0.23x** -- the
WRONG SIGN against a real 4.38x -- and killed the two obvious explanations by
measurement: the defocus rate (flat across a 12x sweep) and the occluder's
luminance step (0.24x -> 0.28x).  The leading surviving candidate is geometry:
the control occluder is a field of ~55 latent-px discs, i.e. effectively
single-scale and far coarser than the ~12 px defocus blur, so a veiled pixel
sits on ONE smooth boundary that sharpens exactly once (at foreground focus).
That is a mechanism for SUPPRESSING multi-peakedness.

This varies occluder geometry and nothing else.  Radiometry, PSD shaping,
noise, breathing, coverage target, seed and defocus rate are all held fixed.

THE GATE IS THE ORACLE TEST, NOT M21'S DETECTOR (discipline 297).  A plant that
cannot express the effect under a perfect depth-step oracle cannot be used to
score any detector for it, so M21's detector is reported for reference only and
is NOT the criterion.

    PASS     truth-gated veiled enrichment >= 1.50x
    PARTIAL                                 1.00x - 1.50x
    FAIL                                  < 1.00x

Invalidating conditions, also pre-registered:
    placebo (frame permutation) must read 1.00 +/- 0.15
    overall multi-peak on strong pixels must land in 2 % - 40 %

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/17-multiscale-occluder.py
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
OUT = os.path.join(HERE, "..", "data", "multiscale-occluder.txt")
REAL = r"C:\dev\macro\test\coffee-bean"
CROP = (600, 1624, 900, 1924)
CFA, SUPERSAMPLE, MARGIN, SUB, K = 2048, 2, 40, 5, 21
NEAR, FAR, COC = 4.0, 16.0, 1.0
REAL_ENRICH = 4.38
LINES = []

# (label, kwargs to two_layer_occlusion, is-the-control)
VARIANTS = [
    ("discs (control, single-scale)", dict(shape="discs"), True),
    ("discs-powerlaw r^-3, 2-160px", dict(shape="discs-powerlaw"), False),
    ("fractal beta_mask 2.6", dict(shape="fractal", mask_beta=2.6), False),
    ("fractal beta_mask 1.6", dict(shape="fractal", mask_beta=1.6), False),
]


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


def cfg(coc, margin_px=MARGIN, n=K):
    return RenderConfig(
        sensor=C.A7C2,
        optics=Optics(n_marked=11.0, magnification=2.0, pupil_ratio=1.0),
        capture=Capture(iso=50.0, n_frames=n, coc_px_per_frame=coc),
        breathing=Breathing(total_scale_change=-0.04575,
                            centre_x_px=-22.0, centre_y_px=-113.0),
        margin_px=margin_px, seed=1, channels="green", depth_bands=1)


def enrich(mp, hi, lo):
    if hi.sum() < 500 or lo.sum() < 500:
        return float("nan"), float("nan"), float("nan")
    a = mp[hi].mean() * 100.0
    b = mp[lo].mean() * 100.0
    return a, b, a / max(b, 1e-9)


def main():
    t0 = time.time()
    say("Is multi-scale occluder geometry the missing ingredient?  "
        "(question 132)")
    say("PRE-REGISTERED in M25-simulator-measured.md section 11, "
        "committed ce92597 before this script existed.")
    say("GATE: truth-gated veiled enrichment.  "
        "PASS >= 1.50x / PARTIAL 1.00-1.50x / FAIL < 1.00x")
    say(f"Real coffee-bean (M21): {REAL_ENRICH}x.  "
        "Section 4.3 control measured 0.23x.")
    say()

    # ---- real radiometry, exactly as section 4.3 --------------------------
    fs = sorted(glob_mod.glob(os.path.join(REAL, "*.ARW")))[::SUB]
    import rawpy
    G = []
    for f in fs:
        with rawpy.imread(f) as rr:
            # AGENTS rule 32: raw_image_visible is a view into LibRaw's buffer
            # and dies with the `with` block.  astype() copies, inside.
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
    freq, amp, hist = B.calibrate_psd(cfg(COC, margin_px=24), (512, 512),
                                      base_e, ce, beta, 101, tf, tp,
                                      float(peak), iters=4)
    psd = (freq, amp)
    say(f"real: ISO {iso:.0f} (g={nm.gain_dn_per_e:.5f} DN/e-, fact 200 "
        f"corrected), mean {mid.mean():.0f} DN, sd {mid.std():.0f} DN, "
        f"beta {beta:.3f}, peak frame {peak}")
    say("PSD shaping mismatch by iteration: "
        + ", ".join(f"{h:.4f}" for h in hist))
    say(f"defocus: coc {COC} px/frame, fg at index {NEAR:.0f}, bg at "
        f"{FAR:.0f} -> {abs(FAR - NEAR) * COC:.0f} px of blur separation")
    say()

    gain = lv / lv[len(G) // 2]
    prng = np.random.default_rng(20260823)
    rows = []

    for label, kw, is_ctrl in VARIANTS:
        tr = time.time()
        sc = SC.two_layer_occlusion(
            (CFA, CFA), SUPERSAMPLE, base_e, ce, base_e * 1.25, ce * 1.25,
            FAR, NEAR, edge_frac=0.35, beta=beta, seed=7,
            margin=MARGIN, psd=psd, **kw)

        # geometry of the occluder actually built, before any rendering
        al = sc.layers[1].alpha
        gy, gx = np.gradient(al)
        per = float(np.sqrt(gy * gy + gx * gx).sum()) / al.size
        feat = 1.0 / max(per, 1e-9)

        st = render_stack(sc, cfg(COC), gain_series=gain)
        Gs = (st.frames[:, 0::2, 1::2].astype(np.float32) - 512)
        say(f"--- {label} ---")
        say(f"  occluder: coverage {al.mean() * 100:.1f}%, mean feature "
            f"~{feat:.1f} latent px ({feat / SUPERSAMPLE:.1f} sensor px), "
            f"render {time.time() - tr:.0f}s")

        V2 = np.stack([ff(g, 2) for g in Gs])
        V13 = np.stack([ff(g, 13) for g in Gs])
        _, c13, am13 = multipeak(V13)
        amr = median_filter(am13.astype(np.float32), 5)
        step = np.abs(np.gradient(amr)[0]) + np.abs(np.gradient(amr)[1])
        strong = c13 > 0.10
        mp, _, _ = multipeak(V2)

        # ---- ground truth, which no real capture can supply ---------------
        vf = st.truth["visible_focus"][0::2, 1::2]
        af = st.truth["alpha_front"][0::2, 1::2]
        tstep = (np.abs(np.gradient(vf)[0])
                 + np.abs(np.gradient(vf)[1])) >= 1.0
        tpartial = (af > 0.02) & (af < 0.98)

        tru_lo = strong & ~tstep & ~tpartial
        veiled = strong & tpartial
        est_hi = strong & (step >= 1.0)
        est_lo = strong & (step < 0.25)

        va, vb, ve = enrich(mp, veiled, tru_lo)
        ea, eb, ee = enrich(mp, est_hi, est_lo)

        # ---- placebo: permute frame order, noise statistics preserved -----
        perm = prng.permutation(len(Gs))
        V2p = V2[perm]
        mpp, _, _ = multipeak(V2p)
        _, _, pe = enrich(mpp, veiled, tru_lo)

        base = mp[strong].mean() * 100.0
        say(f"  truly-veiled px {int(veiled.sum()):>7}   "
            f"truly-smooth px {int(tru_lo.sum()):>7}")
        say(f"  ORACLE (truth-gated veiled) : {va:5.2f}% veiled vs "
            f"{vb:5.2f}% smooth = {ve:5.2f}x   <-- THE GATE")
        say(f"  placebo (permuted frames)   : {pe:5.2f}x")
        say(f"  M21 estimated step map      : {ee:5.2f}x  "
            f"(reference only, not the gate)")
        say(f"  overall multi-peak on strong pixels: {base:.1f}%  "
            f"(real 4.8%, sanity band 2-40%)")
        say()
        rows.append((label, feat, ve, pe, ee, base, is_ctrl))

    # ---- verdict ---------------------------------------------------------
    say("=" * 78)
    say(f"{'occluder':32} {'feat px':>8} {'ORACLE':>8} {'placebo':>8} "
        f"{'M21':>7} {'base%':>7}")
    for label, feat, ve, pe, ee, base, is_ctrl in rows:
        say(f"{label:32} {feat:>8.1f} {ve:>7.2f}x {pe:>7.2f}x "
            f"{ee:>6.2f}x {base:>6.1f}%")
    say(f"{'REAL coffee-bean (M21)':32} {'--':>8} {'--':>8} {'--':>8} "
        f"{REAL_ENRICH:>6.2f}x {4.8:>6.1f}%")
    say()

    ctrl = [r for r in rows if r[6]][0]
    test = [r for r in rows if not r[6]]
    bad_placebo = [r for r in rows if not (0.85 <= r[3] <= 1.15)]
    bad_base = [r for r in rows if not (2.0 <= r[5] <= 40.0)]

    say(f"control reproduced {ctrl[2]:.2f}x "
        f"(section 4.3 measured 0.23x; prediction 2 said +/-0.04 -> "
        f"{'HELD' if abs(ctrl[2] - 0.23) <= 0.04 else 'MISSED'})")
    if bad_placebo:
        say("INVALID: placebo outside 1.00 +/- 0.15 on "
            + ", ".join(r[0] for r in bad_placebo))
    if bad_base:
        say("NOT SCORED: base rate outside 2-40 % on "
            + ", ".join(r[0] for r in bad_base))

    scorable = [r for r in test
                if 0.85 <= r[3] <= 1.15 and 2.0 <= r[5] <= 40.0]
    say()
    if not scorable:
        say("VERDICT: NO ADMISSIBLE VARIANT.  Every multi-scale occluder "
            "violated an invalidating condition, so this run says nothing "
            "about question 132.")
        return 0
    best = max(scorable, key=lambda r: r[2])
    say(f"best admissible variant: {best[0]} at {best[2]:.2f}x")
    if best[2] >= 1.50:
        say("VERDICT: PASS.  Multi-scale occluding structure IS the missing "
            "ingredient.  The plant can express veiling under a perfect "
            "oracle, so M21's detector becomes scoreable on it -- which is "
            "the next step, NOT a claim made by this run.")
    elif best[2] >= 1.00:
        say("VERDICT: PARTIAL.  Occluder geometry repairs the SIGN of the "
            "effect but not its magnitude.  Geometry is A cause, not THE "
            "cause, and the plant is still not fit to score M21's detector.")
    else:
        say("VERDICT: FAIL.  Multi-scale occluding structure is NOT the "
            "missing ingredient.  Question 132's leading hypothesis is "
            "closed and effort should be redirected away from geometry.")
    say(f"[{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
