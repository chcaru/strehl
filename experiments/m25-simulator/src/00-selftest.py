"""00 -- simulator self-tests: does it do what it claims, before any gate.

These are internal consistency checks with hard PASS/FAIL, in the spirit of
`m9-support`'s `selftest`.  They are **not** validation against reality -- that
is Gate 1.  Their job is to stop a coding error being reported as a physics
result.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/00-selftest.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import optics as OP                              # noqa: E402
from strehl_sim import scene as SC                               # noqa: E402
from strehl_sim import sensor as SE                              # noqa: E402
from strehl_sim.config import (A7C2, FPN_SIGMA_DN, TEMPORAL_SIGMA_DN,  # noqa
                               Breathing, Capture, Optics, fpn_sigma_dn)
from strehl_sim.focus import NoiseModel                          # noqa: E402
from strehl_sim.render import RenderConfig, render_stack, similarity_warp  # noqa

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "data", "selftest.txt")
LINES = []
OK = [0, 0]


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def check(cond, msg):
    if cond:
        OK[0] += 1
        say(f"  PASS  {msg}")
    else:
        OK[1] += 1
        say(f"  FAIL  {msg}")


def group_a_optics():
    say("group A -- optics reproduce the project's own optical facts")
    o = Optics(n_marked=11.0, magnification=2.0, pupil_ratio=1.0)
    check(abs(o.bellows - 3.0) < 1e-9,
          f"bellows factor B = 1 + m/p = {o.bellows:.3f} (fact 27: 2.41-3.06)")
    check(abs(o.n_eff - 33.0) < 1e-9,
          f"N_eff = N_marked * B = f/{o.n_eff:.1f} at marked f/11")
    fc = o.cutoff_cyc_per_px(A7C2.pixel_pitch_um, 550.0)
    check(abs(fc - 0.2821) < 0.002,
          f"diffraction cutoff {fc:.4f} cyc/px vs M5's measured knee "
          f"0.2762 at f/11 (fact 27)")

    # Fact 12: MTF at sensor Nyquist is 0.000 at marked f/8 and f/11 once the
    # bellows factor is applied, and the extinction aperture is N_eff ~ 18.6.
    for marked in (8.0, 11.0):
        oo = Optics(n_marked=marked, magnification=2.0, pupil_ratio=1.0)
        m = OP.diffraction_otf(np.array([[0.5]]),
                               oo.cutoff_cyc_per_px(A7C2.pixel_pitch_um,
                                                    550.0))[0, 0]
        check(m < 1e-9, f"MTF at Nyquist is {m:.4f} at marked f/{marked:.0f} "
                        f"(N_eff f/{oo.n_eff:.0f}) -- fact 12")
    n_ext = A7C2.pixel_pitch_um / (550.0 * 1e-3 * 0.5)
    check(abs(n_ext - 18.62) < 0.05,
          f"cutoff reaches Nyquist at N_eff = f/{n_ext:.2f} (M5: f/18.6)")

    # The OTFs are normalised and monotone where they should be.
    fr = np.linspace(0, 0.6, 200).reshape(1, -1)
    d = OP.diffraction_otf(fr, 0.2821)
    check(abs(d[0, 0] - 1.0) < 1e-9, "diffraction OTF is 1.0 at DC")
    check(np.all(np.diff(d[0]) <= 1e-12), "diffraction OTF is monotone")
    df = OP.defocus_otf(fr, 6.0)
    check(abs(df[0, 0] - 1.0) < 1e-9, "defocus OTF is 1.0 at DC")
    check(df.min() < -0.01, "defocus OTF goes negative (contrast reversal is "
                            "modelled, not clipped)")
    say()


def group_b_noise():
    say("group B -- the noise chain reproduces the calibrated model")
    rng = np.random.default_rng(4242)
    for iso in (160.0, 500.0):
        nm = NoiseModel.for_iso(iso)
        for level_dn in (200.0, 2000.0, 8000.0):
            e = np.full((512, 512), level_dn / nm.gain_dn_per_e)
            dn = SE.expose(e, iso, A7C2, None, rng).astype(np.float64)
            got = dn.std()
            want = np.sqrt(nm.variance(level_dn))
            check(abs(got / want - 1.0) < 0.03,
                  f"ISO {iso:.0f} at {level_dn:.0f} DN: sigma {got:.3f} vs "
                  f"model {want:.3f} ({got / want:.3f}x)")

    # Dark frames against M4's measured temporal sigma table.  This is a real
    # comparison with reality, not an internal check, and it is reported even
    # where it disagrees.
    say("  dark-frame temporal sigma vs M4 §8 (MEASURED comparison):")
    say(f"    {'ISO':>5} {'simulated':>10} {'M4':>10} {'ratio':>7}")
    worst = 0.0
    for iso in (50, 100, 200, 400, 1000, 2000):
        nm = NoiseModel.for_iso(float(iso))
        e = np.zeros((256, 256))
        fr = np.stack([SE.expose(e, float(iso), A7C2, None, rng)
                       .astype(np.float64) for _ in range(20)])
        sig = float(fr.std(axis=0, ddof=1).mean())
        m4 = TEMPORAL_SIGMA_DN[iso]
        say(f"    {iso:>5} {sig:>10.4f} {m4:>10.4f} {sig / m4:>7.3f}")
        worst = max(worst, abs(sig / m4 - 1.0))
    check(worst < 0.25,
          f"noise model is within 25% of M4's measured dark sigma at EVERY "
          f"ISO including 50, once g uses max(ISO,100) (worst "
          f"{worst * 100:.1f}%)")

    # FPN is FIXED: it must survive frame averaging.
    fixed = SE.FixedPattern((2048, 2048), 160.0, A7C2, seed=7)
    check(abs(fixed.dsnu.std() / fpn_sigma_dn(160.0) - 1.0) < 0.05,
          f"DSNU sd {fixed.dsnu.std():.4f} DN vs M4 interpolated "
          f"{fpn_sigma_dn(160.0):.4f} DN at ISO 160")
    check(abs(fixed.n_hot / (2048 * 2048) - A7C2.hot_fraction) < 2e-5,
          f"hot pixels {fixed.n_hot} of 2048^2 = "
          f"{100 * fixed.n_hot / 2048 ** 2:.4f}% (M22: 0.0346%)")
    hv = fixed.hot.reshape(-1)[fixed.hot_idx]
    check(abs(hv.mean() - A7C2.hot_mean_dn) < 0.6
          and abs(float(np.median(hv))) < 1e-9,
          f"excess ACROSS FLAGGED PIXELS: mean {hv.mean():.3f} DN, median "
          f"{float(np.median(hv)):.3f} DN (M22: +3.0 mean, 0.0 median)")
    say()


def group_c_cfa():
    say("group C -- CFA sampling is aperture-integrate-then-select")
    rng = np.random.default_rng(11)
    S = 4
    ch = np.zeros((32, 32, 3))
    ch[..., 0] = 100.0
    ch[..., 1] = 200.0
    ch[..., 2] = 300.0
    m = SE.mosaic(ch)
    check(m[0, 0] == 100 and m[0, 1] == 200 and m[1, 0] == 200
          and m[1, 1] == 300,
          "RGGB layout matches raw_pattern [[0,1],[3,2]] "
          "(R,G1 / G2,B in row-major)")

    lat = np.arange(16 * 16 * S * S, dtype=np.float64).reshape(16 * S, 16 * S)
    box = SE.pixel_aperture_integrate(lat, S)
    want = lat[:S, :S].mean()
    check(abs(box[0, 0] - want) < 1e-9,
          "pixel aperture is the mean of the S x S latent block")

    # The pixel aperture must attenuate like a box one sensor pitch wide.  The
    # S-tap discrete box is an approximation to the continuous integral with
    # error O((f/S)^2); measured at f = 0.25 cyc/px it should be within a
    # percent of sinc(f).  Measured by DFT bin, because a cosine sampled near
    # Nyquist has a phase-dependent peak-to-peak and reading max-min there is
    # a trap I fell into once already.
    n = 64
    f = 0.25
    x = np.arange(n * S) / S
    sig = np.tile(np.cos(2 * np.pi * f * x), (8, 1))
    got = SE.pixel_aperture_integrate(sig, S)
    bin_k = int(round(f * n))
    amp = 2.0 * abs(np.fft.rfft(got[0])[bin_k]) / n
    check(abs(amp / np.sinc(f) - 1.0) < 0.02,
          f"aperture MTF at {f} cyc/px = {amp:.4f} vs sinc({f}) = "
          f"{np.sinc(f):.4f} ({amp / np.sinc(f):.4f}x)")
    say()


def group_d_occlusion():
    """The claim that matters most: occlusion is composited AFTER per-layer
    blur, and that is measurably different from blurring a composite."""
    say("group D -- occlusion is rendered physically (blur then composite)")
    S = 3
    m = 24
    hw = (96, 96)
    # The two layers must differ in LEVEL, not just texture, or the plant
    # cannot express the effect it is meant to detect (rule 13 / discipline
    # 24).  A first version gave both layers 4000 e- and "failed" for want of
    # any contrast to veil; see the report's mistakes section.
    sc = SC.two_layer_occlusion(hw, S,
                                bg_e=2000, bg_contrast_e=150,
                                fg_e=8000, fg_contrast_e=600,
                                bg_focus=16.0, fg_focus=4.0,
                                shape="halfplane", seed=3, margin=m)
    cfg = RenderConfig(sensor=A7C2, optics=Optics(11.0, 2.0, 1.0),
                       capture=Capture(iso=160.0, n_frames=21,
                                       coc_px_per_frame=2.0),
                       breathing=Breathing(total_scale_change=0.0),
                       margin_px=m, seed=5, shot=False, read=False, fpn=False)
    st = render_stack(sc, cfg)
    g1, g2 = SE.green_planes(st.frames.astype(np.float64) - A7C2.black)
    g = 0.5 * (g1 + g2)

    # With the foreground 12 frames out of focus at the background's best
    # frame, a background pixel a few px behind the edge is VEILED: its level
    # must sit strictly between the unoccluded background and the fully
    # occluded foreground.
    k_bg = 16
    edge_g = hw[1] // 4                      # edge column in green-plane px
    fr = g[k_bg]
    bg_far = fr[:, 4:12].mean()
    fg_far = fr[:, -12:-4].mean()
    veil = fr[:, edge_g - 4:edge_g - 1].mean()
    check(min(bg_far, fg_far) < veil < max(bg_far, fg_far),
          f"pixels behind the edge are veiled: {veil:.1f} DN lies between "
          f"background {bg_far:.1f} and foreground {fg_far:.1f}")

    # The background must still be resolvable behind the veil: its through-
    # focus curve at a veiled pixel must still peak near the BACKGROUND's
    # focus frame.  Blur-after-composite destroys exactly this.
    from strehl_sim import optics as _o
    cache = _o.OtfCache(sc.layers[0].radiance.shape[:2], S,
                        A7C2.pixel_pitch_um, cfg.optics.n_eff)
    a = np.clip(sc.layers[1].alpha, 0, 1)
    sharp = a * sc.layers[1].radiance + (1 - a) * sc.layers[0].radiance

    def crop(x):
        return SE.pixel_aperture_integrate(
            x[m * S:(m + hw[0]) * S, m * S:(m + hw[1]) * S], S)

    # Wrong order: composite the sharp layers, THEN apply the depth-dependent
    # blur, normalised the same way the right order is.
    num = np.zeros_like(sharp)
    den = np.zeros_like(sharp)
    right = np.zeros(sc.layers[0].radiance.shape[:2])
    for lay in sc.layers:
        h = cache.total(abs(k_bg - float(lay.focus)) * 2.0, 535.0, True)
        al = np.clip(lay.alpha, 0, 1)
        vis = al if lay is sc.layers[-1] else (1 - a)
        num += _o.blur(sharp * vis, h)
        den += _o.blur(vis, h)
        C = _o.blur(lay.radiance * al, h)
        A = np.clip(_o.blur(al, h), 0, 1)
        right = C + (1 - A) * right
    wrong = crop(num / np.maximum(den, 1e-9))
    rightc = crop(right)
    band = slice(hw[1] // 2 - 24, hw[1] // 2 + 24)
    rel = (np.abs(rightc[:, band] - wrong[:, band]).mean()
           / rightc[:, band].mean())
    check(rel > 0.02,
          f"blur-then-composite differs from composite-then-blur by "
          f"{rel * 100:.1f}% of level in a 48 px band at the edge")
    say()


def group_e_geometry():
    say("group E -- breathing is a similarity about a centre, not parallax")
    img = np.zeros((256, 256))
    img[100:156, 100:156] = 1.0
    w = similarity_warp(img, 1.01, 128.0, 128.0, 0.0, 0.0, 0.0, 3)
    check(abs(w.sum() / img.sum() - 1.01 ** 2) < 0.02,
          f"a +1% scale grows area by {w.sum() / img.sum():.4f} (expect "
          f"{1.01 ** 2:.4f})")
    ident = similarity_warp(img, 1.0, 128.0, 128.0, 0.0, 0.0, 0.0, 3)
    check(np.array_equal(ident, img), "unit scale is a true identity "
                                      "(no resampling loss when nothing moves)")
    # Discipline 11: the resampler is not neutral; state its cost.
    r = similarity_warp(similarity_warp(img, 1.05, 128, 128, 0, 0, 0, 3),
                        1 / 1.05, 128, 128, 0, 0, 0, 3)
    say(f"    round-trip cubic resample RMS error: "
        f"{np.sqrt(((r - img) ** 2).mean()):.5f} of unit contrast "
        f"(discipline 11: resampling is not neutral)")
    say()


def main():
    t0 = time.time()
    say("strehl_sim self-test")
    say()
    group_a_optics()
    group_b_noise()
    group_c_cfa()
    group_d_occlusion()
    group_e_geometry()
    say(f"{OK[0]} passed, {OK[1]} failed   [{time.time() - t0:.1f}s]")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 1 if OK[1] else 0


if __name__ == "__main__":
    raise SystemExit(main())
