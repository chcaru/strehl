"""10 -- render the M67 plants.

Writes, per plant, three files under `experiments/M67-focus-correctness/plants`:

    <name>.meta.txt      key/value, one per line
    <name>.frames.u16    K * (2*plane_h) * (2*plane_w) little-endian u16 CFA
    <name>.truth.f32     plane_h * plane_w float32, the visible focus in
                         frame-index units at PLANE resolution

`truth` is the 2x2 block mean of `render.ground_truth`'s `visible_focus`, which
is the scene's own geometric focus map composited under UNBLURRED alpha and
integrated over the pixel aperture.  It is computed from scene geometry and the
frame focus planes and never touches Tenengrad, the regulariser or the gate --
that is the whole reason this plant exists.  The block mean is taken because a
plane pixel owns the 2x2 sensor quad at `(2*px, 2*py)` (`plane.rs`), so the
plane-resolution truth is the quad's mean depth.  The Rust side rounds it to an
index and also uses the continuous value, so the defocus statistic does not
inherit the rounding.

Deviations from `strehl_sim`'s defaults are the ones registered in
`PREREGISTRATION.md` section 2: breathing off, no photometric drift,
`channels="green"`, ISO 160, supersample 2, `depth_bands = 2*span + 1`.

    $env:PYTHONIOENCODING='utf-8'
    python -u experiments/M67-focus-correctness/src/10-render-plants.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
M25 = os.path.normpath(os.path.join(HERE, "..", "..", "m25-simulator", "src"))
sys.path.insert(0, M25)

from strehl_sim import build as B                    # noqa: E402
from strehl_sim import config as C                   # noqa: E402
from strehl_sim import scene as SC                   # noqa: E402
from strehl_sim import stackio as S                  # noqa: E402
from strehl_sim.render import render_stack           # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, "..", "plants"))
LOG = os.path.normpath(os.path.join(HERE, "..", "out", "10-render-plants.log"))
REAL = r"D:\personal\macro\109MSDCF"
REAL_ROI = S.Roi(2272, 1344, 256, 256)

ISO = 160.0
K = 25
SUPERSAMPLE = 2
BETA_COFFEE = 3.454          # M25 section 4.3: coffee-bean's low-band slope

LINES: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    LINES.append(s)


def sim_noise_sd_dn(mean_dn: float, iso: float) -> float:
    """`sigma(S) = sqrt(g*S_e + (RN_e*g)^2)` in DN, on the GREEN LUMA plane.

    Luma is `(G1 + G2)/2`, so its variance is a quarter of the sum of the two
    greens' -- i.e. half of one green's.  Stated explicitly because getting
    this factor wrong is the difference between a 0.9:1 and a 1.3:1 SNR claim.
    """
    sensor = C.A7C2
    g = sensor.gain_dn_per_e(iso)
    rn = sensor.read_noise_e(iso)
    sig_e = max(mean_dn, 0.0) / g
    var_one_green = g * g * (sig_e + rn * rn)
    return float(np.sqrt(var_one_green / 2.0))


def plane_luma(frame: np.ndarray) -> np.ndarray:
    g1, g2 = S.green_planes(frame)
    return 0.5 * (np.maximum(g1.astype(np.float64) - 512.0, 0.0)
                  + np.maximum(g2.astype(np.float64) - 512.0, 0.0))


def block_mean_2x2(a: np.ndarray) -> np.ndarray:
    h, w = a.shape
    return a[: h // 2 * 2, : w // 2 * 2].reshape(h // 2, 2, w // 2, 2) \
            .mean(axis=(1, 3))


def render_one(name: str, side: int, coc: float, contrast_mult: float,
               beta: float, span: float, seed: int,
               base_e: float, contrast_e: float) -> None:
    t0 = time.time()
    bands = max(1, int(2 * span + 1))
    B.set_supersample(SUPERSAMPLE)
    cfg = B.cfg_109(coc, n_frames=K, seed=seed, channels="green",
                    depth_bands=bands)
    # Registered deviation: the merge assumes registered frames, so the plant
    # carries no focus breathing.  A warped plant would score the aligner.
    cfg.breathing = C.Breathing(total_scale_change=0.0, centre_x_px=0.0,
                                centre_y_px=0.0)
    ce = contrast_e * contrast_mult
    hw = (side, side)
    if span <= 0.0:
        sc = SC.flat_texture(hw, SUPERSAMPLE, base_e, ce, (K - 1) / 2.0,
                             beta=beta, seed=100 + seed, margin=cfg.margin_px)
    else:
        lo = (K - 1) / 2.0 - span / 2.0
        hi = (K - 1) / 2.0 + span / 2.0
        sc = SC.tilted_plane(hw, SUPERSAMPLE, base_e, ce, lo, hi, axis="x",
                             beta=beta, seed=100 + seed, margin=cfg.margin_px)
    st = render_stack(sc, cfg)

    vf = st.truth["visible_focus"].astype(np.float64)
    truth = block_mean_2x2(vf).astype(np.float32)
    ph, pw = truth.shape

    # Achieved structure-to-noise, measured on the band of the frame that is
    # actually in focus there.  For the flat plant that is the whole field.
    kc = (K - 1) // 2
    lum = plane_luma(st.frames[kc])
    if span > 0.0:
        centre = np.argmin(np.abs(truth.mean(axis=0) - kc))
        x0 = max(0, int(centre) - 32)
        x1 = min(pw, int(centre) + 32)
    else:
        x0, x1 = pw // 4, 3 * pw // 4
    band = lum[ph // 4: 3 * ph // 4, x0:x1]
    mean_dn = float(band.mean())
    sd_dn = float(band.std())
    noise_dn = sim_noise_sd_dn(mean_dn, ISO)
    struct_dn = float(np.sqrt(max(sd_dn ** 2 - noise_dn ** 2, 0.0)))

    os.makedirs(OUT, exist_ok=True)
    st.frames.astype("<u2").tofile(os.path.join(OUT, f"{name}.frames.u16"))
    truth.astype("<f4").tofile(os.path.join(OUT, f"{name}.truth.f32"))
    meta = {
        "plant": "flat" if span <= 0 else "tilt",
        "side": side,
        "plane_w": pw,
        "plane_h": ph,
        "frames": K,
        "iso": ISO,
        "black": 512,
        "white": 15360,
        "camera": "ILCE-7CM2",
        "coc_px_per_frame": coc,
        "span_frames": span,
        "beta": beta,
        "contrast_mult": contrast_mult,
        "latent_contrast_e": round(ce, 3),
        "latent_base_e": round(base_e, 3),
        "seed": seed,
        "supersample": SUPERSAMPLE,
        "depth_bands": bands,
        "breathing_scale_change": 0.0,
        "infocus_band_mean_dn": round(mean_dn, 4),
        "infocus_band_sd_dn": round(sd_dn, 4),
        "infocus_band_model_noise_dn": round(noise_dn, 4),
        "infocus_band_structure_dn": round(struct_dn, 4),
        "infocus_band_snr": round(struct_dn / max(noise_dn, 1e-9), 4),
        "render_seconds": round(time.time() - t0, 1),
    }
    with open(os.path.join(OUT, f"{name}.meta.txt"), "w",
              encoding="utf-8") as fh:
        for k, v in meta.items():
            fh.write(f"{k} {v}\n")
    say(f"{name:<44} plane {pw}x{ph}  truth {truth.min():.2f}..{truth.max():.2f}"
        f"  snr {meta['infocus_band_snr']:>7.3f}"
        f"  ({meta['render_seconds']:.0f}s)")


def main() -> int:
    t0 = time.time()
    say("M67 -- rendering the plants")
    raw = S.load_real(REAL)
    iso_real = S.iso_of(REAL)
    _, rval = S.tiles(raw, REAL_ROI, 0)
    ref = rval[raw.shape[0] // 2]
    base_e, contrast_e = B.fit_radiometry(ref, iso_real)
    beta = B.fit_beta(ref)
    del raw
    say(f"radiometry fitted from {REAL} {REAL_ROI} (read-only): "
        f"base {base_e:.1f} e-, contrast {contrast_e:.1f} e- sd, "
        f"beta {beta:.3f}; real ROI mean {ref.mean():.2f} DN "
        f"sd {ref.std():.4f} DN, ISO {iso_real}")
    say(f"plants render at ISO {ISO}, K {K}, supersample {SUPERSAMPLE}, "
        f"breathing 0.0, gain drift 0.0, channels=green")
    say()

    jobs = []
    # Headline cell: three seeds at the larger plane.
    for s in (1, 2, 3):
        jobs.append(dict(name=f"tilt-s1024-coc10-c4-b{int(beta*1000)}-span24-seed{s}",
                         side=1024, coc=1.0, contrast_mult=4.0, beta=beta,
                         span=24.0, seed=s))
    # Sweep: defocus rate x subject contrast, two seeds.
    for coc, ctag in ((1.0, "10"), (3.0, "30")):
        for cm in (1.0, 4.0, 16.0):
            for s in (1, 2):
                jobs.append(dict(
                    name=f"tilt-s512-coc{ctag}-c{int(cm)}-b{int(beta*1000)}"
                         f"-span24-seed{s}",
                    side=512, coc=coc, contrast_mult=cm, beta=beta,
                    span=24.0, seed=s))
    # Narrower depth span, and the degenerate fronto-parallel cell.
    for span, tag in ((8.0, "span8"), (0.0, "span0")):
        for s in (1, 2):
            jobs.append(dict(
                name=f"{'tilt' if span else 'flat'}-s512-coc10-c4"
                     f"-b{int(beta*1000)}-{tag}-seed{s}",
                side=512, coc=1.0, contrast_mult=4.0, beta=beta,
                span=span, seed=s))
    # Subject spectrum axis: coffee-bean's low-band slope.
    for s in (1, 2):
        jobs.append(dict(
            name=f"tilt-s512-coc10-c4-b{int(BETA_COFFEE*1000)}-span24-seed{s}",
            side=512, coc=1.0, contrast_mult=4.0, beta=BETA_COFFEE,
            span=24.0, seed=s))

    say(f"{len(jobs)} plants queued")
    stride, offset = 1, 0
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == "--stride":
            stride = int(argv[i + 1])
        elif a == "--offset":
            offset = int(argv[i + 1])
    for i, j in enumerate(jobs):
        if i % stride != offset:
            continue
        # Skip-if-exists lets several workers share one job list, and lets a
        # stopped run resume without re-rendering finished plants.
        done = os.path.join(OUT, j["name"] + ".meta.txt")
        blob = os.path.join(OUT, j["name"] + ".truth.f32")
        if os.path.exists(done) and os.path.exists(blob):
            say(f"{j['name']:44s} already rendered, skipping")
            continue
        render_one(base_e=base_e, contrast_e=contrast_e, **j)

    say()
    say(f"total {time.time() - t0:.0f}s")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(f"{LOG}.{offset}", "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {LOG}.{offset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
