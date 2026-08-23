"""09 -- is Gate 2's NC-B blind spot the gate's fault or the knob's?

Gate 2 found that dropping diffraction does NOT move Gate 1's statistics
outside tolerance.  There are two very different explanations:

  (a) the `with_diffraction` knob does nothing, i.e. the simulator never
      applied a diffraction PSF and the whole term is a no-op;
  (b) the knob works, the image really does change, and Gate 1's statistics
      are simply insensitive to it.

Those have opposite implications for the report, so this measures which.  Two
noise-free in-focus single-frame renders of the SAME latent scene, no contrast
re-calibration, and their radially averaged power spectra.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/09-diffraction-effect.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import build as B                                # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402
from strehl_sim.config import Capture, Optics                    # noqa: E402
from strehl_sim.render import render_stack                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "diffraction-effect.txt")
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def radial_power(a):
    a = np.asarray(a, np.float64)
    a = a - a.mean()
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    p = np.abs(np.fft.rfft2(a * win)) ** 2
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.rfftfreq(a.shape[1])[None, :]
    fr = np.sqrt(fy * fy + fx * fx)
    edges = np.linspace(0.0, 0.5, 51)
    idx = np.clip(np.digitize(fr.ravel(), edges) - 1, 0, len(edges) - 2)
    tot = np.bincount(idx, weights=p.ravel(), minlength=len(edges) - 1)
    cnt = np.bincount(idx, minlength=len(edges) - 1)
    return 0.5 * (edges[:-1] + edges[1:]), tot / np.maximum(cnt, 1)


def main():
    say("Is NC-B's blind spot the gate's or the knob's?")
    say()
    B.set_supersample(3)
    hw = (1024, 1024)
    base_e, contrast_e, beta = 5515.4, 111.8, 1.651
    out = {}
    for diff in (True, False):
        cfg = B.cfg_109(1.5, n_frames=1, seed=1, channels="green")
        cfg.with_diffraction = diff
        cfg.shot = cfg.read = cfg.fpn = False
        cfg.capture = Capture(iso=160.0, n_frames=1, coc_px_per_frame=1.5)
        sc = B.flat_scene(cfg, hw, base_e, contrast_e, beta,
                          focus_index=0.0, seed=101)
        st = render_stack(sc, cfg, scale_series=np.array([1.0]),
                          focus_planes=np.array([0.0]))
        g = S.green_value(st.frames[0]).astype(np.float64)
        f, p = radial_power(g)
        out[diff] = (float(g.std()), f, p)
        say(f"with_diffraction={str(diff):<5}  in-focus green structure sd "
            f"{g.std():.4f} DN")
    r = out[False][0] / out[True][0]
    say(f"structure sd ratio (no-diffraction / diffraction) = {r:.4f}")
    say()
    o = Optics(n_marked=11.0, magnification=2.0, pupil_ratio=1.0)
    ne = o.n_eff() if callable(getattr(o, "n_eff", None)) else o.n_eff
    say(f"N_eff = {float(ne):.2f}  (marked f/11 at m=2.0, p=1.0)")
    say()
    say("radially averaged power, green plane (cycles per green px):")
    say(f"  {'freq':>7} {'diffr':>12} {'no-diffr':>12} {'ratio':>8}")
    f, pd = out[True][1], out[True][2]
    pn = out[False][2]
    for i in range(1, len(f), 4):
        if pd[i] <= 0:
            continue
        say(f"  {f[i]:>7.3f} {pd[i]:>12.4g} {pn[i]:>12.4g} "
            f"{pn[i] / pd[i]:>8.3f}")
    say()
    hi = (f > 0.30) & (f < 0.48)
    amp = np.sqrt(pn[hi].sum() / max(pd[hi].sum(), 1e-30))
    say(f"amplitude ratio over 0.30-0.48 cyc/green-px: {amp:.3f}x")
    say("VERDICT: the knob is " + ("a NO-OP -- the simulator never applied "
                                   "diffraction" if abs(r - 1) < 0.01 and
                                   abs(amp - 1) < 0.02 else
                                   "REAL; the rendered image changes "
                                   "materially, so Gate 1 is simply "
                                   "insensitive to it"))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
