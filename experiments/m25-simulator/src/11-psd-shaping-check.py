"""11 -- does spectrum shaping actually deliver the real subject's spectrum?

`10-spectrum-check.py` measured the mechanism behind Gate 1c's failure: at
`coffee-bean`'s crop the simulated green plane carries **6.2x too much** power
below 0.2 cyc/green-px and **0.43x too little** above 0.3, because a single
fitted power law is a bad model of a real subject and the optical chain then
reddens it again.

`scene.shaped_texture` + `build.calibrate_psd` replace the single slope with a
measured radial profile.  This checks the fix in isolation -- one noisy frame,
no gates, no stack -- before spending half an hour re-running Gate 1c on it.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/11-psd-shaping-check.py
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
OUT = os.path.join(HERE, "..", "data", "psd-shaping-check.txt")
SUPERSAMPLE = 2
SIZE = 512
COC = 12.0
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def green_of(path, crop=None):
    import rawpy
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        g = 0.5 * (v[0::2, 1::2].astype(np.float64)
                   + v[1::2, 0::2].astype(np.float64)) - 512.0
    return g[crop[0]:crop[1], crop[2]:crop[3]] if crop else g


def cfg(iso, noise=True):
    c = RenderConfig(
        sensor=A7C2,
        optics=Optics(n_marked=11.0, magnification=2.0, pupil_ratio=1.0),
        capture=Capture(iso=iso, n_frames=1, coc_px_per_frame=COC),
        breathing=Breathing(total_scale_change=0.0),
        margin_px=16, seed=1, channels="green")
    c.shot = c.read = c.fpn = noise
    return c


def band(f, p, lo, hi):
    return float(p[(f >= lo) & (f <= hi)].sum())


def render(iso, base_e, ce, beta, psd):
    sc = SC.flat_texture((2 * SIZE, 2 * SIZE), SUPERSAMPLE, base_e, ce, 0.0,
                         beta=beta, seed=101, margin=16, psd=psd)
    st = render_stack(sc, cfg(iso), scale_series=np.array([1.0]),
                      focus_planes=np.array([0.0]))
    return S.green_value(st.frames[0]).astype(np.float64)


def main():
    say("Does PSD shaping deliver the real subject's spectrum?")
    say()
    B.set_supersample(SUPERSAMPLE)
    fb = sorted(glob.glob(os.path.join(r"C:\dev\macro\test\coffee-bean",
                                       "*.ARW")))[::5]
    real = green_of(fb[10], (600, 1624, 900, 1924))[:SIZE, :SIZE]
    iso = 50.0
    nm = F.NoiseModel.for_iso(iso)
    base_e, contrast_e = B.fit_radiometry(real, iso)
    beta = B.fit_beta(real)
    tf, tp, nv, clamped = B.target_psd(real, iso)
    say(f"real crop {real.shape}: mean {real.mean() + 512:.1f} DN, "
        f"sd {real.std():.2f} DN, fitted beta {beta:.3f}")
    say(f"modelled flat noise power {nv:.3g} DN^2/bin; "
        f"{clamped} of {len(tf)} bins clamped at the noise floor "
        f"(structure NOT measurable there)")
    say(f"target structure sd from the PSD: {np.sqrt(tp.sum() * 0):.0f}"
        if False else "")

    target_struct = contrast_e * nm.gain_dn_per_e
    c0 = cfg(iso)
    freq, amp, hist = B.calibrate_psd(c0, (2 * SIZE, 2 * SIZE), base_e,
                                      contrast_e, beta, 101, tf, tp, 0.0,
                                      iters=4)
    say(f"calibrate_psd shape mismatch (median |log ratio|) by iteration: "
        + ", ".join(f"{h:.4f}" for h in hist))
    say()

    rows = []
    for label, psd in (("single power law (old)", None),
                       ("shaped PSD (new)", (freq, amp))):
        ce = contrast_e
        for _ in range(3):
            g = render(iso, base_e, ce, beta, psd)
            got = float(g.std())
            ce *= np.sqrt(max(target_struct ** 2, 1.0)
                          / max(got ** 2 - nv, 1.0))
        fr, pr = B.radial_power(real)
        fs, ps = B.radial_power(g)
        say(f"--- {label} ---   sim sd {g.std():.2f} DN "
            f"(real {real.std():.2f})")
        say(f"  {'band':<14} {'real P':>11} {'sim P':>11} {'sim/real':>9}")
        r = {}
        for lo, hi in [(0.02, 0.05), (0.05, 0.10), (0.10, 0.20),
                       (0.20, 0.30), (0.30, 0.40), (0.40, 0.50)]:
            a, b = band(fr, pr, lo, hi), band(fs, ps, lo, hi)
            r[(lo, hi)] = b / max(a, 1e-30)
            say(f"  {f'{lo:.2f}-{hi:.2f}':<14} {a:>11.4g} {b:>11.4g} "
                f"{b / max(a, 1e-30):>9.3f}")
        rows.append((label, r))
        say()

    say("=" * 78)
    say(f"  {'band':<14} {'old':>9} {'new':>9}")
    for k in rows[0][1]:
        say(f"  {f'{k[0]:.2f}-{k[1]:.2f}':<14} {rows[0][1][k]:>9.3f} "
            f"{rows[1][1][k]:>9.3f}")
    worst_old = max(abs(np.log(v)) for v in rows[0][1].values())
    worst_new = max(abs(np.log(v)) for v in rows[1][1].values())
    say(f"worst band error: old {np.exp(worst_old):.2f}x, "
        f"new {np.exp(worst_new):.2f}x")
    say("VERDICT: " + ("shaping helps" if worst_new < worst_old
                       else "shaping does NOT help -- do not use it"))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
