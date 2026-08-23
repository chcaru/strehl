"""10 -- where does the simulated image's spatial spectrum stop matching?

Gate 1c failed: the simulated occlusion cell produced 28.5 % multi-peak
pixels where M21 measures 4.8 % on the real `coffee-bean`, and enrichment
collapsed to 0.77x.  Gate 1b's simulated speckle also runs high, and the
wide-support measures under-produce excess.  All three are consistent with one
hypothesis: **the simulated image has too little fine-scale structure**, so a
small-support focus operator sees mostly noise.

`fit_beta` fits the spectral slope on the *observed* real green plane and then
the latent field with that slope is pushed through the optical chain, which
reddens it *again*.  `calibrate_contrast` corrects the amplitude; nothing
corrects the slope.  That is a plausible mechanism.  This measures whether it
is the actual one, by comparing real and simulated radially averaged power
spectra band by band on the same two ROIs the gates use.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/10-spectrum-check.py
"""

from __future__ import annotations

import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import build as B                                # noqa: E402
from strehl_sim import focus as F                                # noqa: E402
from strehl_sim import scene as SC                               # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402
from strehl_sim.config import A7C2, Breathing, Capture, Optics   # noqa: E402
from strehl_sim.render import RenderConfig, render_stack         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "spectrum-check.txt")
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def radial_power(a, nb=64):
    a = np.asarray(a, np.float64)
    a = a - a.mean()
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    p = np.abs(np.fft.rfft2(a * win)) ** 2
    p /= (win ** 2).sum()
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.rfftfreq(a.shape[1])[None, :]
    fr = np.sqrt(fy * fy + fx * fx)
    edges = np.linspace(0.0, 0.5, nb + 1)
    idx = np.clip(np.digitize(fr.ravel(), edges) - 1, 0, nb - 1)
    tot = np.bincount(idx, weights=p.ravel(), minlength=nb)
    cnt = np.bincount(idx, minlength=nb)
    ok = cnt > 0
    return 0.5 * (edges[:-1] + edges[1:])[ok], tot[ok] / cnt[ok]


def band_slope(f, p, lo, hi):
    m = (f >= lo) & (f <= hi) & (p > 0)
    if m.sum() < 3:
        return float("nan")
    return float(-np.polyfit(np.log(f[m]), np.log(p[m]), 1)[0])


def band_amp(f, p, lo, hi):
    m = (f >= lo) & (f <= hi)
    return float(p[m].sum())


def green_of(path, crop=None):
    import rawpy
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        g = 0.5 * (v[0::2, 1::2].astype(np.float64)
                   + v[1::2, 0::2].astype(np.float64)) - 512.0
    if crop:
        g = g[crop[0]:crop[1], crop[2]:crop[3]]
    return g


def sim_frame(iso, coc, size, base_e, contrast_e, beta, n_marked=11.0,
              supersample=3, noise=True, focus=0.0):
    cfg = RenderConfig(
        sensor=A7C2,
        optics=Optics(n_marked=n_marked, magnification=2.0, pupil_ratio=1.0),
        capture=Capture(iso=iso, n_frames=1, coc_px_per_frame=coc),
        breathing=Breathing(total_scale_change=0.0),
        margin_px=16, seed=1, channels="green")
    cfg.shot = cfg.read = cfg.fpn = noise
    B.set_supersample(supersample)
    sc = SC.flat_texture((2 * size, 2 * size), supersample, base_e,
                         contrast_e, focus, beta=beta, seed=101, margin=16)
    st = render_stack(sc, cfg, scale_series=np.array([1.0]),
                      focus_planes=np.array([focus]))
    return S.green_value(st.frames[0]).astype(np.float64)


def compare(label, real_g, iso, coc, supersample):
    nm = F.NoiseModel.for_iso(iso)
    base_e, contrast_e = B.fit_radiometry(real_g, iso)
    beta = B.fit_beta(real_g)
    size = min(real_g.shape[0], real_g.shape[1], 512)
    rg = real_g[:size, :size]
    target = contrast_e * nm.gain_dn_per_e
    ce = contrast_e
    for _ in range(2):
        sg = sim_frame(iso, coc, size, base_e, ce, beta,
                       supersample=supersample)
        st_sd = float(np.std(sg))
        nv = 0.5 * (nm.gain_dn_per_e * base_e * nm.gain_dn_per_e
                    + (nm.read_noise_e * nm.gain_dn_per_e) ** 2)
        ce *= np.sqrt(max(target ** 2, 1.0)
                      / max(st_sd ** 2 - nv, 1.0))
    fr, pr = radial_power(rg)
    fs, ps = radial_power(sg)
    say(f"--- {label} (ISO {iso:.0f}, coc {coc}, S={supersample}) ---")
    say(f"  real  mean {rg.mean() + 512:.1f} DN  sd {rg.std():.3f} DN   "
        f"fitted beta {beta:.3f}")
    say(f"  sim   mean {sg.mean() + 512:.1f} DN  sd {sg.std():.3f} DN")
    say(f"  {'band (cyc/green-px)':<22} {'real P':>12} {'sim P':>12} "
        f"{'sim/real':>9}")
    for lo, hi in [(0.02, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
                   (0.30, 0.40), (0.40, 0.50)]:
        a, b = band_amp(fr, pr, lo, hi), band_amp(fs, ps, lo, hi)
        say(f"  {f'{lo:.2f}-{hi:.2f}':<22} {a:>12.4g} {b:>12.4g} "
            f"{b / max(a, 1e-30):>9.3f}")
    say(f"  slope over 0.02-0.20: real {band_slope(fr, pr, 0.02, 0.20):+.3f}  "
        f"sim {band_slope(fs, ps, 0.02, 0.20):+.3f}")
    say(f"  slope over 0.20-0.45: real {band_slope(fr, pr, 0.20, 0.45):+.3f}  "
        f"sim {band_slope(fs, ps, 0.20, 0.45):+.3f}")
    nvar = 0.5 * (nm.gain_dn_per_e * (rg.mean())
                  + (nm.read_noise_e * nm.gain_dn_per_e) ** 2)
    say(f"  modelled white-noise power per bin ~ {nvar:.3g} DN^2 "
        f"(flat across f)")
    say()
    return dict(label=label, beta=beta,
                hi_ratio=band_amp(fs, ps, 0.30, 0.50)
                / max(band_amp(fr, pr, 0.30, 0.50), 1e-30))


def main():
    say("Where does the simulated spatial spectrum stop matching the real one?")
    say("(radially averaged power of the green plane, Hann-windowed, "
        "black-subtracted)")
    say()
    res = []
    f109 = sorted(glob.glob(os.path.join(r"C:\dev\macro\test\109MSDCF",
                                         "*.ARW")))
    g = green_of(f109[11])[1344:1344 + 256, 2272:2272 + 256]
    res.append(compare("109MSDCF flat ROI 2272,1344", g, 160.0, 1.5, 3))

    fb = sorted(glob.glob(os.path.join(r"C:\dev\macro\test\coffee-bean",
                                       "*.ARW")))[::5]
    gb = green_of(fb[10], (600, 1624, 900, 1924))
    res.append(compare("coffee-bean M21 crop", gb, 50.0, 12.0, 2))

    say("=" * 78)
    for r in res:
        say(f"{r['label']:<32} sim/real power over 0.30-0.50 cyc/px = "
            f"{r['hi_ratio']:.3f}x")
    say()
    say("READ: a ratio below 1 means the simulator delivers LESS fine-scale")
    say("structure than reality at the same total sd, which is exactly what")
    say("would inflate speckle, depress wide-support excess, and flood the")
    say("R=2 multi-peak detector with noise-driven peaks.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
