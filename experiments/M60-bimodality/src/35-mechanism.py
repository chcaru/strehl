"""35 -- why S0 flags only 2% of veiled pixels: H-A and H-B compounded.

S0's test is not a prominence test.  It requires a peak to clear its IMMEDIATE
frame neighbours by 0.04 x range.  So the quantity that must clear the bar is the
largest single-frame step into the peak, not the peak's prominence over its dip.

T2 measured the bar at 4.336 DN on veiled pixels.  S2 measured the prominence
there at 7.600 DN -- above the bar.  Yet S0 flags 1.97% of them.  This resolves
that apparent contradiction by measuring the quantity S0 actually tests.

No new hypothesis: this is the mechanism behind T1 and T2, measured rather than
argued.  Uses the frames frozen by 30-render-m25-plant.py.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/M60-bimodality/src/35-mechanism.py
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
from scipy.ndimage import sobel, uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m60lib as L                                               # noqa: E402

DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
PLANT = os.path.join(DATA, "30-m25-plant.npz")
OUT = os.path.join(DATA, "35-mechanism.txt")
OUTJ = os.path.join(DATA, "35-mechanism.json")
MC_REPS, SEED = 16, 20260827
LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def ff(g, R):
    gx = sobel(g, axis=1, mode='reflect') / 8.0
    gy = sobel(g, axis=0, mode='reflect') / 8.0
    return uniform_filter(np.sqrt(gx * gx + gy * gy), 2 * R + 1)


def main() -> None:
    t0 = time.time()
    rng0 = np.random.default_rng(SEED)
    d = np.load(PLANT)
    G, vf, af = d["frames"], d["visible_focus"], d["alpha_front"]
    iso, n = float(d["iso"]), d["frames"].shape[0]

    say("M60b/35 -- the quantity S0 actually tests, measured")
    say()
    V2 = np.stack([ff(G[k], 2) for k in range(n)])
    V13 = np.stack([ff(G[k], 13) for k in range(n)])
    Vs13 = np.copy(V13)
    Vs13[1:-1] = (V13[:-2] + 2 * V13[1:-1] + V13[2:]) / 4.0
    c13 = (Vs13.max(0) - Vs13.min(0)) / np.maximum(Vs13.max(0), 1e-6)
    strong = c13 > 0.10
    tstep = (np.abs(np.gradient(vf)[0]) + np.abs(np.gradient(vf)[1])) >= 1.0
    tpartial = (af > 0.02) & (af < 0.98)
    veiled, smooth = strong & tpartial, strong & ~tstep & ~tpartial
    say(f"POWER: veiled {int(veiled.sum())}  smooth {int(smooth.sum())}")
    say()

    Vs = np.copy(V2)
    Vs[1:-1] = (V2[:-2] + 2 * V2[1:-1] + V2[2:]) / 4.0
    rngmap = Vs.max(0) - Vs.min(0)
    bar = 0.04 * rngmap

    # the second peak, and the largest single-frame step into it
    S = np.repeat(L.focus_sigma_mc(G.mean(0), 2, iso, MC_REPS, rng0)[None], n, 0)
    r2 = L.second_peak(Vs)
    k2 = r2["k2"]
    prom = r2["prom"]
    idx = np.arange(n)[:, None, None]
    up = np.diff(Vs, axis=0)                       # Vs[k+1]-Vs[k]
    rise_in = np.take_along_axis(up, np.maximum(k2 - 1, 0)[None], 0)[0]
    fall_out = -np.take_along_axis(up, np.minimum(k2, n - 2)[None], 0)[0]
    step = np.minimum(rise_in, fall_out)           # what S0's AND-test needs

    say("The two quantities, on the SAME pixels.")
    say("NOTE: prominence here is measured on the [1,2,1]-smoothed cube, which")
    say("is what S0 operates on. M60's S2 prominence is on the raw cube (rule")
    say("23, no frame-axis smoothing), so the two are not the same number.")
    say(f"{'population':<12}{'prominence':>12}{'S0 step':>10}{'S0 bar':>10}"
        f"{'step/bar':>10}{'prom/bar':>10}")
    rows = {}
    for nm, sel in (("veiled", veiled), ("smooth", smooth)):
        p = float(np.median(prom[sel]))
        st = float(np.median(step[sel]))
        bb = float(np.median(bar[sel]))
        say(f"{nm:<12}{p:11.3f} {st:9.3f} {bb:9.3f} {st/bb:9.3f} {p/bb:9.3f}")
        rows[nm] = dict(prom=p, step=st, bar=bb, step_bar=st / bb,
                        prom_bar=p / bb)
    say()
    say("  The signal is the SAME at veiled and smooth pixels "
        f"({rows['veiled']['prom']:.3f} vs {rows['smooth']['prom']:.3f} DN "
        "prominence).")
    say(f"  The BAR is {rows['veiled']['bar']/rows['smooth']['bar']:.2f}x higher "
        "at veiled pixels. That is H-A, and it alone costs a factor of "
        f"{rows['smooth']['prom_bar']/rows['veiled']['prom_bar']:.2f} in "
        "prom/bar.")
    say(f"  S0 tests the STEP, not the prominence, and the step is "
        f"{rows['veiled']['prom']/max(rows['veiled']['step'],1e-9):.1f}x "
        "smaller. That is H-B.")
    say()

    say("Peak width, which is what converts prominence into step:")
    for nm, sel in (("veiled", veiled), ("smooth", smooth)):
        w = float(np.median((prom[sel] / np.maximum(step[sel], 1e-6))))
        say(f"  {nm:<8} median prominence / step = {w:6.2f} frames of rise")
        rows[nm]["frames_of_rise"] = w
    say()

    # counterfactual: S0's own rule, prominence-based instead of step-based
    say("Counterfactual -- S0's own 0.04*range bar applied to the PROMINENCE")
    say("instead of to the single-frame step, changing nothing else:")
    fl = prom > bar
    a = fl[veiled].mean() * 100
    b = fl[smooth].mean() * 100
    say(f"  veiled {a:.2f}%   smooth {b:.2f}%   = {a/max(b,1e-9):.2f}x")
    say("  (for reference, S0 as shipped reads 1.97% / 10.61% = 0.19x)")
    rows["prom_bar_counterfactual"] = dict(veiled=float(a), smooth=float(b),
                                           enrich=float(a / max(b, 1e-9)))
    say()
    say(f"total {time.time()-t0:.0f}s")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    with open(OUTJ, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main()
