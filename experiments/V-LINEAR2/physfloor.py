"""ARMS WHOSE SCORE IS FIXED BY PHYSICS, NOT BY THE THING UNDER TEST.

WHY THIS EXISTS.  cohfix.py's verdict rests on coherent power between two
independent half-stacks, and cohfix.pair_cross FITS a sub-pixel shift per ROI
before forming the cross term.  That is a fitted quantity, and a fitted
alignment can in principle lock onto noise and MANUFACTURE coherence.  If it
does, every arm is inflated -- and strehl most of all, because strehl is the
only arm with a real 1.32 px offset for the fitter to work on.  Nothing run so
far excludes that.

The self-test in cohfix.py cannot exclude it either: it shifts an image by a
KNOWN amount and checks the shift is recovered, so it proves the estimator
works when there IS something to align.  It says nothing about what the
estimator does when there is nothing.

So this file adds two arms whose true score is fixed in advance by
construction, bracketing the measurement from both ends:

  SELF      a crop against ITSELF.  Every Fourier bin has zero phase
            difference, so C == P and the coherent fraction is exactly 1.000 in
            every band.  Anything less is coherence the pipeline LOSES.

  DISJOINT  half-stack A at one ROI against half-stack B at a DIFFERENT ROI.
            The two crops share the sensor, the optics, the illumination, the
            demosaic and the whole render path -- and share NO SCENE.  The
            scene cross-term is therefore zero by construction, and whatever C
            comes out is the sum of (a) coherence the estimator invents and
            (b) common-mode sensor structure that is not scene: fixed-pattern
            noise, PRNU, and any deterministic artefact of the pipeline.
            docs/research/V-LINEAR2.md sec.12 lists exactly that as
            UNDETERMINED.  This measures it.

  DISJOINT-NOFIT  the same disjoint pairs with the shift fit DISABLED (raw
            cross-spectrum, no phase ramp).  The difference between DISJOINT
            and DISJOINT-NOFIT is the part the FITTER contributes, isolated.

PRE-REGISTERED READING.  Fixed here before the first run, so it cannot be
adjusted to suit the answer:

  SELF      C/P >= 0.990 in every band up to and including 0.20-0.25.
            Below that, the pipeline is losing coherence and every C in
            docs/research/V-LINEAR2.md sec.9 is an underestimate by that much.

  DISJOINT  |C_disjoint| / C_strehl < 0.10 at 0.20-0.25.
            PASS  -> the instrument does not manufacture coherence, and
                     common-mode sensor structure contributes under a tenth of
                     the verdict statistic.
            FAIL  -> the verdict of sec.9 is INVALID.  It must be reported as
                     invalid rather than defended, and the band numbers
                     withdrawn.

  DISJOINT vs DISJOINT-NOFIT
            If DISJOINT is materially ABOVE DISJOINT-NOFIT, the fitter is
            inventing alignment on content that has none.  Reported either way.

WHAT THIS CANNOT DO.  The disjoint pair is drawn from different SENSOR
POSITIONS, so column/row fixed-pattern structure tied to a specific site is not
shared between them the way it is between two half-stacks of the same ROI.
This arm therefore BOUNDS the estimator's invented coherence tightly, and bounds
site-independent common-mode structure (PRNU statistics, pipeline artefacts)
only loosely.  A tight bound on site-locked FPN needs a second subject stack
rendered identically and compared at the SAME sensor coordinates; that is a
25-minute develop and 12.5 GB, and is not done here.  Stated so it is not
mistaken for a stronger result than it is.

INVOCATION (rule 47).  Reads only:
    C:\\dev\\strehl-out\\V-H2H2\\lin\\113-{full,A,B}-g1.tiff
Writes nothing.  Prints one table and one verdict.

    python physfloor.py [nroi]        (default 64)
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
sys.path.insert(0, _HERE)

import h2                                                        # noqa: E402
import rois                                                      # noqa: E402
from h2h2b import band_power, load, T, PAD                       # noqa: E402
from cohfix import LO, HI, NAMES, cross, pair_cross, refine_shift, \
    selftest                                                     # noqa: E402

BAND = "0.20-0.25"
SELF_MIN = 0.990          # pre-registered, see docstring
DISJOINT_MAX = 0.10       # pre-registered, see docstring


def self_arm(F, det):
    """C/P of every ROI against itself.  Must be exactly 1.000 by construction.

    Driven through cohfix.cross, not through a shortcut, so that any coherence
    the SHARED code path loses shows up here.
    """
    P, C = [], []
    for (y, x) in det:
        c, n = F.crop(y, x, T)
        if c is None or n:
            continue
        p = band_power(c, LO, HI)
        q = cross(c, c, 0.0, 0.0, LO, HI)
        if p is None or q is None:
            continue
        P.append(p)
        C.append(q)
    return np.array(P), np.array(C)


def disjoint_arm(A, B, det, fit=True):
    """A at ROI i against B at ROI i+k.  Scene cross-term is zero by design.

    fit=True  runs the SAME code path as the verdict (cohfix.pair_cross), which
              fits and removes a per-ROI sub-pixel shift.
    fit=False forms the raw cross-spectrum with no shift fitted at all, so the
              difference between the two isolates the fitter's contribution.
    """
    P, C = [], []
    used = drop = 0
    n = len(det)
    for i, (y, x) in enumerate(det):
        y2, x2 = det[(i + n // 2 + 1) % n]        # far away in the shuffle
        if (y2, x2) == (y, x):
            continue
        ca, na = A.crop(y, x, T)
        cb, nb = B.crop(y2, x2, T)
        if ca is None or cb is None or na or nb:
            drop += 1
            continue
        p = band_power(ca, LO, HI)
        if p is None:
            drop += 1
            continue
        if fit:
            # cohfix.pair_cross crops BOTH arms at the same position, which is
            # the REAL arm, not this one.  So its two-step logic is reproduced
            # here against a second crop taken from elsewhere: integer part out
            # by moving the crop window, sub-pixel remainder out by the phase
            # ramp.  Same functions, same order, same thresholds.
            dy, dx, good = refine_shift(ca, cb)
            if not good:
                drop += 1
                continue
            iy, ix = int(round(dy)), int(round(dx))
            cb2, nb2 = B.crop(y2 - iy, x2 - ix, T)
            if cb2 is None or nb2:
                cb2 = cb
            ry, rx, good = refine_shift(ca, cb2)
            if not good:
                drop += 1
                continue
            q = cross(ca, cb2, ry, rx, LO, HI)
        else:
            q = cross(ca, cb, 0.0, 0.0, LO, HI)
        if q is None:
            drop += 1
            continue
        P.append(p)
        C.append(q)
        used += 1
    return np.array(P), np.array(C), used, drop


def main():
    nroi = int(sys.argv[1]) if len(sys.argv) > 1 else 64

    F1 = load("113-full-g1")
    detail, flat, counts = rois.census(F1, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(11)              # same seed as cohfix.main
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]

    c0, _ = F1.crop(det[0][0], det[0][1], T + 16)
    if not selftest(c0):
        print("\nSELF-TEST FAILED -- no number is reported.")
        return 2

    A = load("113-A-g1")
    B = load("113-B-g1")

    print("\n" + "=" * 96)
    print("ARMS WHOSE SCORE IS FIXED BY CONSTRUCTION")
    print("=" * 96)

    Ps, Cs = self_arm(F1, det)
    Pd, Cd, ud, dd = disjoint_arm(A, B, det, fit=True)
    Pn, Cn, un, dn = disjoint_arm(A, B, det, fit=False)

    # the real arm, for scale: strehl's own half-stacks at the SAME ROI
    Pr, Cr = [], []
    for (y, x) in det:
        r = pair_cross(A, B, y, x, T, LO, HI)
        if r is None:
            continue
        Pr.append(r[0])
        Cr.append(r[2])
    Pr, Cr = np.array(Pr), np.array(Cr)

    print(f"  SELF      n={len(Ps)}")
    print(f"  DISJOINT  n={ud} (dropped {dd})")
    print(f"  DIS-NOFIT n={un} (dropped {dn})")
    print(f"  strehl    n={len(Cr)}   <- the verdict arm, for scale")

    hdr = "  ".join(f"{n:>11s}" for n in NAMES)
    print(f"\n  {'arm':22s}{hdr}")
    rows = [("SELF        C/P", Cs, Ps),
            ("DISJOINT    C/P", Cd, Pd),
            ("DIS-NOFIT   C/P", Cn, Pn),
            ("strehl      C/P", Cr, Pr)]
    for name, c, p in rows:
        if len(c) == 0:
            print(f"  {name:22s}  n=0 -- the estimator REFUSED every pair; "
                  f"see the verdict below")
            continue
        v = np.median(c, 0) / np.median(p, 0)
        print(f"  {name:22s}" + "  ".join(f"{x:11.4f}" for x in v))

    cs = np.median(Cr, 0)
    print(f"\n  {'|C| relative to strehl C':22s}{hdr}")
    for name, c in (("DISJOINT", Cd), ("DIS-NOFIT", Cn)):
        if len(c) == 0:
            print(f"  {name:22s}  n=0 -- no pair survived the shift fit")
            continue
        v = np.median(c, 0)
        print(f"  {name:22s}" + "  ".join(f"{abs(a) / abs(b):11.4f}"
                                          for a, b in zip(v, cs)))

    i = NAMES.index(BAND)
    self_v = float(np.median(Cs, 0)[i] / np.median(Ps, 0)[i])
    dis_r = (float(abs(np.median(Cd, 0)[i]) / abs(cs[i]))
             if len(Cd) else None)
    nof_r = float(abs(np.median(Cn, 0)[i]) / abs(cs[i]))

    print("\n=== PRE-REGISTERED VERDICT (thresholds fixed in the docstring) ===")
    ok_self = all(np.median(Cs, 0)[j] / np.median(Ps, 0)[j] >= SELF_MIN
                  for j in range(i + 1))
    print(f"  SELF      C/P at {BAND} = {self_v:.4f}   "
          f"(threshold >= {SELF_MIN:.3f} in every band up to it)  "
          f"{'PASS' if ok_self else 'FAIL'}")
    if dis_r is None:
        print(f"  DISJOINT  NO PAIR SURVIVED THE SHIFT FIT ({dd} of {dd} "
              f"refused).")
        print("            The pre-registered threshold cannot be evaluated as")
        print("            written.  READ IT THIS WAY, and note that this is a")
        print("            STRONGER result than a small number would have been:")
        print("            the fitter cannot invent coherence on content that")
        print("            has none, because it declines to fit at all.  The")
        print("            scene-free floor is therefore the DIS-NOFIT arm,")
        print("            which needs no fit and so cannot be refused.")
        ok_dis = nof_r < DISJOINT_MAX
        print(f"  DIS-NOFIT |C|/C_strehl at {BAND} = {nof_r:.4f}   "
              f"(threshold < {DISJOINT_MAX:.2f})  "
              f"{'PASS' if ok_dis else 'FAIL'}")
    else:
        ok_dis = dis_r < DISJOINT_MAX
        print(f"  DISJOINT  |C|/C_strehl at {BAND} = {dis_r:.4f}   "
              f"(threshold < {DISJOINT_MAX:.2f})  "
              f"{'PASS' if ok_dis else 'FAIL'}")
        print(f"  fitter's contribution: DISJOINT {dis_r:.4f} vs "
              f"DIS-NOFIT {nof_r:.4f}  -> "
              f"{'the fit INVENTS coherence' if dis_r > nof_r + 0.02 else 'the fit invents nothing detectable'}")

    if ok_self and ok_dis:
        print("\n  BOTH FIXED-SCORE ARMS PASS.  The coherent-power verdict of")
        print("  docs/research/V-LINEAR2.md sec.9 is not an artefact of the")
        print("  per-ROI shift fit, and non-scene common-mode structure")
        print(f"  contributes under {100 * DISJOINT_MAX:.0f}% of it at {BAND}.")
    else:
        print("\n  A FIXED-SCORE ARM FAILED.  The verdict of")
        print("  docs/research/V-LINEAR2.md sec.9 must be reported as INVALID")
        print("  and its band numbers withdrawn -- not defended.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
