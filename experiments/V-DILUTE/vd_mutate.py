# -*- coding: utf-8 -*-
"""CONCLUSION-FLIP MUTATION TEST of vd_xsig.py's commissioning gates.

ORCH, correction #5 item 3: a presence-test cannot detect a reversed
conclusion; commission with a mutation that flips the CONCLUSION, not one that
perturbs a number. V-LINEAR ran this on itself and found four flips missed at
88/88 green.

The conclusion under test is the one I am about to report:

    "coffee-bubbles carries NO real content at 0.30-0.35 cyc/px."

So each arm below is a plausible implementation error that would REVERSE or
FABRICATE that verdict, and the question asked of each is not "does the number
move" but "do my two gates (NULL < 0.05, POTENCY > 0.90) still go green while
the verdict changes". An arm that flips the verdict at green is a defect in my
instrument, not in the mutation.

I predicted arm `contiguous` would defeat the gates BEFORE running this, and
recorded the reasoning in the arm's own comment. Both gates use a STATIC
synthetic field, and a static field is invariant to how frames are split, so
no static commissioning arm can see a split that decorrelates focus-varying
content. If that prediction holds, my gates are insufficient as written.
"""
from __future__ import print_function

import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vd_xsig as X                                             # noqa: E402

# Deliberately NOT rewrapping sys.stdout here. vd_xsig already did it at module
# scope, and wrapping the same buffer twice lets the first wrapper close it on
# collection. A module that is ever imported must not touch sys.stdout; since
# vd_xsig does, the importer must simply inherit it.

I32 = X.BANDS.index((0.30, 0.35))
I10 = X.BANDS.index((0.10, 0.15))

ORIG_HALVES = X.halves
ORIG_CROSS = X.cross_frac


def m_identity(g):
    return ORIG_HALVES(g)


def m_samehalf(g):
    """Correlate a half with ITSELF: everything reads as pure signal."""
    a, _ = ORIG_HALVES(g)
    return a, a.copy()


def m_contiguous(g):
    """Split by BLOCKS of the focus sweep instead of interleaving.

    PREDICTED TO DEFEAT BOTH GATES. The two halves then see different parts of
    the focus range, so genuinely recovered detail that differs between them
    decorrelates and reads as noise -- the dangerous direction, because it
    disqualifies a band that really does carry signal. Both gates are static
    fields, identical in every frame, so neither can notice.
    """
    n = len(g) // 2
    return g[:n], g[n:2 * n]


def m_noconj(g):
    return ORIG_HALVES(g)


def cross_noconj(a, b, band, _c={}):
    """Re(FA*FB) instead of Re(FA*conj(FB)) -- a sign error in the phase."""
    h, w = a.shape
    if (h, w) not in _c:
        _c[(h, w)] = X._hann2(h, w)
    win = _c[(h, w)]
    FA = np.fft.rfft2((a - a.mean()) * win)
    FB = np.fft.rfft2((b - b.mean()) * win)
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    rad = np.sqrt(fy ** 2 + fx ** 2)
    m = (rad >= band[0]) & (rad < band[1])
    cross = float((FA.real * FB.real - FA.imag * FB.imag)[m].mean())
    auto = float(((FA.real ** 2 + FA.imag ** 2)
                  + (FB.real ** 2 + FB.imag ** 2))[m].mean() / 2.0)
    return cross / auto if auto > 0 else float("nan")


ARMS = [
    ("identity", m_identity, None, "no change; must reproduce the verdict"),
    ("samehalf", m_samehalf, None, "fabricates signal everywhere"),
    ("contiguous", m_contiguous, None, "destroys focus-varying correlation"),
    ("noconj", m_noconj, cross_noconj, "phase sign error in the cross term"),
]


def gates():
    null = X.score(X.synth("flat"), "mean")
    tone = X.score(X.synth("tone"), "mean")
    swp = X.score(X.synth("sweep"), "mean")
    gn = max(abs(v) for v in null) < 0.05
    gt = tone[I32] > 0.90
    gs = swp[I32] > 0.90
    return gn, gt, gs


def main():
    g = X.load_green("coffee-bubbles")
    var0, _r, _gp = X.VP.fit_variance(g[0])
    varp = X.VP.gauss_pyr(var0, 7)
    print("conclusion under test: coffee-bubbles has NO real content at "
          "0.30-0.35\n")
    print("  %-11s %6s %6s %6s %10s %10s  %s"
          % ("arm", "NULL", "POT", "SWEEP", "f@.30-.35", "f@.10-.15",
             "outcome"))
    base32 = base10 = None
    for name, hv, cf, _why in ARMS:
        X.halves = hv
        X.cross_frac = cf if cf is not None else ORIG_CROSS
        gn, gt, gs = gates()
        v = X.score(g, "shipping", varp)
        if name == "identity":
            base32, base10 = v[I32], v[I10]
        green = gn and gt and gs
        # Two ways to be wrong, both scored. The verdict under test is "no
        # content at 0.30-0.35"; but an arm that leaves that verdict intact
        # while corrupting the band that DOES carry content is still a defect,
        # because the next claim I make may well be a positive one.
        flipped = abs(v[I32]) > 0.10
        corrupt = base10 is not None and abs(v[I10] - base10) > 0.10
        if name == "identity":
            outcome = "baseline"
        elif green and flipped:
            outcome = "*** MISSED -- verdict flipped at GREEN ***"
        elif green and corrupt:
            outcome = "*** MISSED -- signal band corrupted at GREEN ***"
        elif green:
            outcome = "green, verdict and signal band both held"
        else:
            outcome = "CAUGHT by %s" % ("NULL" if not gn else
                                        ("POTENCY" if not gt else "SWEEP"))
        print("  %-11s %6s %6s %6s %10.4f %10.4f  %s"
              % (name, "ok" if gn else "FAIL", "ok" if gt else "FAIL",
                 "ok" if gs else "FAIL", v[I32], v[I10], outcome))
    X.halves, X.cross_frac = ORIG_HALVES, ORIG_CROSS
    print("\nbaseline f@0.30-0.35 = %.4f" % base32)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
