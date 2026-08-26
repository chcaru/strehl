"""Is the multi-band arm's extra fine-band energy DETAIL, or is it NOISE?

`bandtrade.py` reports the blend arm carrying more fine-band amplitude than the
shipped merge on `couch-fibers`. That reading on its own is worthless, and
dangerously so: this project has twice been misled by exactly it. One agent
reported "+6.7% gradients, therefore not a blur" while measuring its own
blotchy artifact; another found "+16.8% high-pass energy" on crops chosen for
containing no structure. Extra high-frequency energy is what BOTH a sharper
image and a noisier image look like.

It also matters more here than it would elsewhere. The shipped path's central
claim is that it gets BELOW single-frame noise -- 5.43x against a selector's
0.77x on a known sqrt(30) = 5.48x burst. An arm that removes the rim by being
noisier has not improved this stacker, it has traded one of its two crown
jewels for the other.

THE DISCRIMINATOR
-----------------
Detail and noise separate on WHERE they live. Pixels are ranked by local
variance of a HEAVILY BLURRED luma, and the flattest are kept. Selecting on
COARSE structure while measuring FINE energy matters twice over:

* the coarse field is essentially identical in the two arms, so the pixel set
  is not chosen by either arm's fine-scale behaviour and neither is flattered;
* real detail is, by construction, absent from the flattest regions, so
  whatever fine-band energy remains there is overwhelmingly noise.

In a flat region there is no detail to be sharper about. Higher fine-band RMS
there means more noise, and there is no benign reading of it.

The frozen pixel set is shared by both arms -- the same pixels, chosen once,
from a field neither arm controls.

    python flatnoise.py <label> <control.tiff> <blend.tiff>
    python flatnoise.py --commission <control.tiff>
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter

from bandtrade import blur, luma, read16

FLAT_PCTL = 20.0     # keep the flattest 20% of the frame
COARSE_SIGMA = 6.0   # "structure" scale used only for SELECTING pixels
VAR_WIN = 15         # local-variance window, px


def flat_mask(ctrl: np.ndarray) -> np.ndarray:
    """The flattest FLAT_PCTL% of pixels, judged on COARSE structure only."""
    sm = gaussian_filter(ctrl, COARSE_SIGMA)
    mean = uniform_filter(sm, VAR_WIN)
    var = uniform_filter(sm * sm, VAR_WIN) - mean * mean
    thr = np.percentile(var, FLAT_PCTL)
    return var <= thr


def fine(a: np.ndarray) -> np.ndarray:
    """The finest Laplacian band: one octave of high-pass, where noise lives."""
    return a - blur(a)


def measure(ctrl: np.ndarray, blend: np.ndarray) -> tuple[float, float, float]:
    m = flat_mask(ctrl)
    fc, fb = fine(ctrl)[m], fine(blend)[m]
    rc = float(np.sqrt(np.mean(fc * fc)))
    rb = float(np.sqrt(np.mean(fb * fb)))
    return rc, rb, 100.0 * float(m.mean())


def report(label: str, ctrl: np.ndarray, blend: np.ndarray) -> float:
    rc, rb, pct = measure(ctrl, blend)
    ratio = rb / rc
    print(f"=== {label} ===")
    print(f"  pixel set : flattest {pct:.1f}% of the frame, chosen from a "
          f"sigma-{COARSE_SIGMA:.0f} px blurred field")
    print(f"              (coarse selection, fine measurement -- neither arm "
          f"influences the choice)")
    print(f"  fine-band RMS in flat regions   control {rc:8.2f} DN")
    print(f"                                  blend   {rb:8.2f} DN")
    print(f"  noise ratio blend/control       {ratio:.4f}")
    if ratio > 1.10:
        print(f"  READING: the blend arm is NOISIER by {100*(ratio-1):.1f}% "
              f"-- its extra fine-band energy is at least partly noise")
    elif ratio < 0.90:
        print(f"  READING: the blend arm is QUIETER by {100*(1-ratio):.1f}%")
    else:
        print(f"  READING: noise is within 10% -- extra fine-band energy "
              f"elsewhere is NOT explained by added noise")
    print()
    return ratio


def commission(src: Path) -> int:
    l = luma(read16(src))
    print(f"commissioning flatnoise.py on {src.name}  ({l.shape[1]} x {l.shape[0]} px)")
    print()
    ok = True

    rc, rb, _ = measure(l, l.copy())
    flat = abs(rb / rc - 1.0) < 1e-6
    print(f"NULL (control vs itself): ratio {rb/rc:.6f}, must be 1.000000")
    print(f"     {'PASS' if flat else '*** FAIL -- the null is not flat'}")
    ok &= flat
    print()

    # POSITIVE CONTROL: a LADDER of known white-noise levels. A single plant
    # only shows the detector can be triggered; a ladder shows it responds in
    # proportion, which is what is needed to tell "flat regions unchanged"
    # (ratio ~1.00) from "flat regions up 14%".
    rng = np.random.default_rng(20260825)
    print("POSITIVE CONTROL -- a ladder of known white noise added to the control")
    print(f"  {'sigma DN':>9} {'flat fine RMS':>14} {'ratio':>8}")
    print(f"  {'-'*9} {'-'*14} {'-'*8}")
    ratios = []
    for sigma in (150.0, 300.0, 600.0, 1200.0):
        noisy = l + rng.normal(0.0, sigma, size=l.shape).astype(np.float32)
        rc2, rb2, _ = measure(l, noisy)
        r = rb2 / rc2
        ratios.append(r)
        print(f"  {sigma:>9.0f} {rb2:>14.2f} {r:>8.4f}")
    monotone = all(b > a for a, b in zip(ratios, ratios[1:]))
    # The decision this detector has to support is 1.00 vs 1.14, so it must
    # resolve a rise of that size somewhere on the ladder.
    resolves = max(ratios) > 1.14
    print(f"  response monotone in injected noise : "
          f"{'PASS' if monotone else '*** FAIL'}")
    print(f"  reaches the +14% rise it must adjudicate : "
          f"{'PASS' if resolves else '*** FAIL -- too blunt for the question asked'}")
    ok &= monotone and resolves
    print()

    print("COMMISSIONED -- flatnoise readings are admissible" if ok
          else "*** NOT COMMISSIONED -- withdraw every flatnoise number")
    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--commission":
        return commission(Path(sys.argv[2]))
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    label, cp, bp = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    lc, lb = luma(read16(cp)), luma(read16(bp))
    assert lc.shape == lb.shape, f"shape mismatch {lc.shape} vs {lb.shape}"
    report(label, lc, lb)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
