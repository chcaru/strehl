# -*- coding: utf-8 -*-
"""SPLIT-HALF CROSS-POWER: is there REAL content at 0.30-0.35 cyc/px?

Why this exists. Addendum H.8 item 6 left one loose end: the shipping merge
reports `prem_sig = 6.54e7 > 0` at 0.30-0.35 on real frames, where
`prem_sig = band(real merge) - band(twin merge)`. That subtraction is only as
good as the twin's noise model. If the real frames carry ANY noise the
Gaussian twin does not model -- fixed pattern, demosaic correlation,
quantisation -- then `prem_sig > 0` measures excess NOISE and I would have
mistaken it for signal. The number cannot settle its own interpretation.

This statistic needs no noise model at all. Split the real frames into two
interleaved halves (alternate frames, so the two halves see almost the same
focus distribution), run the SAME operator on each independently, and take the
cross-power between the two outputs in a band:

    frac = <F_A, F_B> / ((|F_A|^2 + |F_B|^2) / 2)

Sensor noise is independent between the halves, so it cancels in the
numerator in expectation while still counting in the denominator. Real static
scene content is common to both halves and survives in both. So `frac` is the
fraction of the band's power that is REAL, on a scale where 0 = pure noise and
1 = pure shared signal, and it never once refers to a model of the noise.

Reported for `mean` (is content present in the average?) and for `shipping`
(does the merge RECOVER content?) -- the second is the one H.8 item 6 asked
about, because selection can in principle recover detail the average destroys.

COMMISSIONED BOTH DIRECTIONS, and the run refuses to report if either fails:
  NULL    flat field + independent noise           -> frac ~ 0 everywhere
  POTENCY flat field + planted 0.32 cyc/px tone    -> frac ~ 1 at 0.30-0.35
Without the potency arm a broken estimator that always returns 0 would look
like a clean "no signal here" verdict, which is the exact error this file is
meant to prevent.
"""
from __future__ import print_function

import io
import os
import sys

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "V-NEVERWORSE"))

import vn_pyr as VP                                              # noqa: E402
from vd_prem_lib import (BETA, SHIP, Stack, _hann2, load_green,  # noqa: E402
                         run_arm)

BANDS = [(0.10, 0.15), (0.17, 0.20), (0.20, 0.25), (0.25, 0.30),
         (0.30, 0.35), (0.35, 0.40), (0.40, 0.45)]


def cross_frac(a, b, band, _cache={}):
    """Fraction of band power common to two independent estimates."""
    h, w = a.shape
    if (h, w) not in _cache:
        _cache[(h, w)] = _hann2(h, w)
    win = _cache[(h, w)]
    FA = np.fft.rfft2((a - a.mean()) * win)
    FB = np.fft.rfft2((b - b.mean()) * win)
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    rad = np.sqrt(fy ** 2 + fx ** 2)
    m = (rad >= band[0]) & (rad < band[1])
    cross = float((FA.real * FB.real + FA.imag * FB.imag)[m].mean())
    auto = float(((FA.real ** 2 + FA.imag ** 2)
                  + (FB.real ** 2 + FB.imag ** 2))[m].mean() / 2.0)
    return cross / auto if auto > 0 else float("nan")


def halves(g):
    """Interleaved split, so both halves see the same focus distribution."""
    return g[0::2], g[1::2]


def score(g, arm, varp=None):
    ga, gb = halves(g)
    n = min(len(ga), len(gb))
    ga, gb = ga[:n], gb[:n]
    if arm == "mean":
        ra, rb = ga.mean(axis=0), gb.mean(axis=0)
    else:
        ra = run_arm(arm, Stack(ga), varp, np.random.default_rng(4242))
        rb = run_arm(arm, Stack(gb), varp, np.random.default_rng(4242))
    return [cross_frac(ra, rb, b) for b in BANDS]


def synth(kind, n=24, h=512, w=512, sd=40.0, seed=7):
    rng = np.random.default_rng(seed)
    base = np.full((h, w), 2000.0)
    tone = 0.0
    if kind in ("tone", "sweep"):
        y, x = np.mgrid[0:h, 0:w]
        tone = 300.0 * np.sin(2.0 * np.pi * 0.32 * x) \
            + 300.0 * np.sin(2.0 * np.pi * 0.32 * y)
    out = []
    for i in range(n):
        # `sweep` ramps the tone's amplitude with FRAME INDEX, which is the
        # one property a focus bracket has and a static field does not. It is
        # the gate that catches a split which decorrelates focus-varying
        # content -- see vd_mutate.py, arm `contiguous`, which passes both
        # static gates while collapsing measured real content 3.3x.
        a = 1.0 if kind != "sweep" else i / float(n - 1)
        out.append(base + a * tone + rng.normal(0.0, sd, (h, w)))
    return np.stack(out)


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "112MSDCF"
    hdr = "  %-9s " % "arm" + " ".join("%9s" % ("%.2f-%.2f" % b)
                                       for b in BANDS)

    print("COMMISSIONING (no subject result is printed unless both pass)\n")
    print(hdr)
    null = score(synth("flat"), "mean")
    tone = score(synth("tone"), "mean")
    swp = score(synth("sweep"), "mean")
    print("  %-9s " % "NULL" + " ".join("%9.4f" % v for v in null))
    print("  %-9s " % "POTENCY" + " ".join("%9.4f" % v for v in tone))
    print("  %-9s " % "SWEEP" + " ".join("%9.4f" % v for v in swp))
    i32 = BANDS.index((0.30, 0.35))
    ok_null = max(abs(v) for v in null) < 0.05
    ok_tone = tone[i32] > 0.90
    ok_swp = swp[i32] > 0.90
    print("\n  null  max|frac| = %.4f   (needs < 0.05)  %s"
          % (max(abs(v) for v in null), "ok" if ok_null else "FAIL"))
    print("  tone  frac@0.30-0.35 = %.4f   (needs > 0.90)  %s"
          % (tone[i32], "ok" if ok_tone else "FAIL"))
    print("  sweep frac@0.30-0.35 = %.4f   (needs > 0.90)  %s"
          % (swp[i32], "ok" if ok_swp else "FAIL"))
    if not (ok_null and ok_tone and ok_swp):
        print("\nREFUSED: instrument failed commissioning, no verdict given")
        return 2

    g = load_green(subj)
    var0, read2, gph = VP.fit_variance(g[0])
    varp = VP.gauss_pyr(var0, 7)
    print("\n\n%s  N=%d   fraction of band power that is REAL "
          "(0 = noise, 1 = signal)\n" % (subj, len(g)))
    print(hdr)
    for arm in ("mean", "shipping", "pool1"):
        v = score(g, arm, varp)
        print("  %-9s " % arm + " ".join("%9.4f" % x for x in v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
