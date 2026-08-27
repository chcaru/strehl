"""Does 8-bit output change a COHERENT-power comparison, or only a power one?

quantfloor.py measured that truncating a 16-bit render to 8 bits RAISES its
normalised 0.20-0.25 band statistic by +14.6% and its raw band power by +30.0%.
`focus-stack` 1.5 writes uint8, so that matters for every power-ratio number in
this lane.

But the VERDICT statistic is not a power ratio.  cohfix.cross computes

    C = sum over the band of Re( F_A * conj(F_B) )

between two INDEPENDENT half-stacks.  Additive noise that is independent
between the halves -- photon noise, and quantisation error, which depends on
each half's own pixel values -- contributes zero to that in expectation, while
contributing positively to P.  So the prediction is:

    C     roughly UNCHANGED by 8-bit truncation
    P     INFLATED  by ~1.30 at 0.20-0.25
    C/P   DEPRESSED by ~1/1.30

If that is right, then (a) C_strehl/C_comp against the 8-bit arm is NOT
flattered by bit depth, and the "conservative by 14.6%" reading would be wrong,
and (b) the 8-bit arm's coherent FRACTION is depressed by bit depth and must
not be quoted without that caveat.

RESULT: THE PREDICTION ABOVE IS REFUTED, and the refutation is kept here rather
than the docstring rewritten.  C rises by +17.9% at 0.20-0.25, not 0%.  The
error in the reasoning is that quantisation error is a DETERMINISTIC function
of the pixel value, and the two half-stacks are images of the SAME SCENE with
nearly the same pixel values -- so their truncation errors are correlated, not
independent, and land in the coherent term.  Bit depth is therefore not neutral
for a coherent-power comparison either; it inflates the 8-bit arm's C, which
runs in that arm's favour.

This does not argue it.  It truncates strehl's OWN two half-stacks to 8 bits,
re-runs the identical measurement path, and reads the answer off the console.
strehl is used as the test article precisely because its 16-bit original is
available, so the 8-bit and 16-bit numbers differ in nothing but bit depth.

INVOCATION (rule 47).  Reads:
    C:\\dev\\strehl-out\\V-H2H2\\lin\\113-{full,A,B}-g1.tiff
Writes nothing.  Prints two tables.

    python quantcoh.py [nroi]        (default 64)
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
sys.path.insert(0, _HERE)

import h2                                                        # noqa: E402
import rois                                                      # noqa: E402
from h2h2b import load, T, PAD                                    # noqa: E402
from cohfix import measure, NAMES, selftest                      # noqa: E402


def to8(a):
    """The same truncation quantfloor.py applies: a plain 8-bit right-shift on
    the u16 render, put back on the 16-bit scale so the two are directly
    comparable.  focus-stack 1.5's observed median (4, from an input median of
    1112) is consistent with exactly this.
    """
    return np.asarray((np.asarray(a, np.uint16) >> 8).astype(np.uint16)) * 256


class Trunc8:
    """A Render with its raw crops truncated to 8 bits, and nothing else
    changed.  Wrapping raw_crop rather than materialising a truncated image
    keeps the linearisation and luma path byte-identical to the 16-bit arm, so
    the only difference between the two arms is the quantiser -- which is the
    whole point of the test.  (7032x4688x3 float64 is 790 MB; several arms are
    open at once.)"""

    def __init__(self, r):
        self.r = r
        self.h, self.w = r.h, r.w
        self.name = r.name + "-8bit"

    def crop(self, y0, x0, t, chan=None):
        blk = self.r.raw_crop(y0, x0, t)
        nclip = int((blk >= 65535).sum() + (blk == 0).sum())
        v = np.asarray(to8(blk), np.float64)
        return h2.luma709(v), nclip


def main():
    nroi = int(sys.argv[1]) if len(sys.argv) > 1 else 64

    F1 = load("113-full-g1")
    detail, flat, counts = rois.census(F1, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(11)          # same seed as cohfix.main
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]

    c0, _ = F1.crop(det[0][0], det[0][1], T + 16)
    if not selftest(c0):
        print("\nSELF-TEST FAILED -- no number is reported.")
        return 2

    A = load("113-A-g1")
    B = load("113-B-g1")
    A8 = Trunc8(A)
    B8 = Trunc8(B)

    print("\n" + "=" * 96)
    print("8-BIT TRUNCATION vs A COHERENT-POWER COMPARISON")
    print("  strehl's own half-stacks, 16-bit against their own 8-bit "
          "truncation, identical code path")
    print("=" * 96)

    r16 = measure(A, B, 1.0, det, F1)
    r8 = measure(A8, B8, 1.0, det, F1)
    print(f"  ROIs used: 16-bit {r16['used']} (dropped {r16['drop']}), "
          f"8-bit {r8['used']} (dropped {r8['drop']})")

    hdr = "  ".join(f"{n:>11s}" for n in NAMES)
    print(f"\n  {'quantity':28s}{hdr}")
    rows = [
        ("P    8-bit / 16-bit", np.median(r8["P"], 0) / np.median(r16["P"], 0)),
        ("C    8-bit / 16-bit",
         np.median(r8["Cfix"], 0) / np.median(r16["Cfix"], 0)),
        ("C/P  8-bit / 16-bit",
         (np.median(r8["Cfix"], 0) / np.median(r8["P"], 0)) /
         (np.median(r16["Cfix"], 0) / np.median(r16["P"], 0))),
    ]
    for name, v in rows:
        print(f"  {name:28s}" + "  ".join(f"{x:11.4f}" for x in v))

    print(f"\n  {'coherent fraction C/P':28s}{hdr}")
    for name, r in (("16-bit", r16), ("8-bit", r8)):
        v = np.median(r["Cfix"], 0) / np.median(r["P"], 0)
        print(f"  {name:28s}" + "  ".join(f"{x:11.4f}" for x in v))

    i = NAMES.index("0.20-0.25")
    dP = rows[0][1][i]
    dC = rows[1][1][i]
    dF = rows[2][1][i]
    print("\n=== READING (fixed in this file's docstring before running) ===")
    print(f"  at 0.20-0.25:  P x{dP:.3f}   C x{dC:.3f}   C/P x{dF:.3f}")
    if abs(dC - 1.0) < 0.05 and dP > 1.10:
        print("  CONFIRMED: 8-bit truncation inflates POWER but leaves COHERENT")
        print("  power alone.  So C_strehl/C_comp against an 8-bit arm is NOT")
        print("  flattered by bit depth -- it is bit-depth-neutral -- while that")
        print("  arm's coherent FRACTION C/P is depressed by a factor of")
        print(f"  {1 / dF:.2f} and must not be quoted without the caveat.")
    elif abs(dC - 1.0) >= 0.05:
        print(f"  REFUTED: coherent power moved by {100 * (dC - 1):+.1f}%, so it")
        print("  is NOT bit-depth-neutral and the verdict against the 8-bit arm")
        print("  carries a bit-depth term of that size.  Report it.")
    else:
        print("  INCONCLUSIVE: power barely moved, so this test article does")
        print("  not exercise the effect.  Do not draw either conclusion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
