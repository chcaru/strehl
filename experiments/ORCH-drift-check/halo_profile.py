"""Absolute halo measurement on a single master. No A/B pair required.

WHY THIS EXISTS
---------------
`veil_accept.py` and `veil_absolute.py` are both COMPARATORS: they need an
on/off pair from the same stack and they answer "did this operator help".
Neither can answer the question a reader of a finished master actually asks:

    does THIS picture have a halo, yes or no, and how big.

Every halo claim this project has made about the shipping pyramid path has been
made by eye on 1:1 crops. Eyes are good at this -- a halo is one of the few
artifacts humans detect better than most metrics -- but "I looked at it" does
not survive being written down as a quality claim, and it does not scale to 26
subjects x every future render.

THE MEASUREMENT
---------------
A stacking halo is a BRIGHT RIM in the background immediately outside a dark
subject's silhouette, produced when a selector picks near-focus foreground
pixels for locations that belong to the background. Its signature in the
luminance profile is an OVERSHOOT: walking outward from the silhouette edge,
background luminance rises ABOVE its own far-field level and then settles back
down to it.

So:

  1. Segment the subject as the dark region against a bright backdrop, using
     Otsu on the luma histogram, then morphological open/close to kill speckle.
  2. Euclidean distance transform outward from the subject.
  3. Median background luma in each distance band.
  4. Far field = the median in the outermost band.
  5. overshoot = max over the NEAR bands of (band_median - far_field).

A positive overshoot is a halo. There is no negative-going defect measurable
this way, and the first version of this file was wrong to claim there was.

WHAT THE COMMISSION TAUGHT THIS FILE
------------------------------------
The first version also reported `veil = min(band)` and called a large negative
value "veiling, the dark aura". Commissioning killed that. On a clean master
the measured profile is:

    d   2-6    6-12    12-20   20-32   32-50   50-80   80-120   far
      -19951  -11512   -5044   -2033   -1193    -758     -432     0

That is a smooth MONOTONE ramp up to the far field with no overshoot anywhere,
and it is the signature of a clean edge -- but `min(band)` reads -19951 on it
and would have declared the cleanest subject in the corpus severely defective.

The near-field deficit is not an artifact at all. It is the subject's own
OUT-OF-FOCUS PENUMBRA: the distance transform starts at a thresholded
silhouette, and immediately outside any real subject there is a soft transition
where the subject's own blurred edge still darkens the background. Every
photograph ever taken has one. It is optics, not stacking.

So the penumbra depth is still printed, because it describes the picture, but
it is explicitly NOT a defect statistic and carries no verdict. This instrument
cannot separate veiling from penumbra and says so rather than reporting a
number that would be read as if it could.

TWO INDEPENDENT HALO SIGNATURES
-------------------------------
`overshoot` is referenced to the far field, so it inherits any error in the far
field. `bump` is not: it is the largest amount by which the profile DECREASES
as you walk outward, and a monotone ramp has bump = 0 by construction. A halo
is a local maximum in the profile, so it raises both. Reporting both means a
halo has to defeat two statistics with different failure modes to hide.


MEDIAN, NOT MEAN, IS LOAD-BEARING
---------------------------------
Background bands near a real subject contain the subject's own out-of-focus
neighbours, stray hairs, and dust. A mean is dragged by them and would report a
halo on any subject with a wispy edge. The median is not.

WHAT IS EXCLUDED, AND COUNTED
-----------------------------
This measurement is only defined where there IS a bright backdrop and a dark
subject with a real silhouette. Subjects that are full-frame texture (`foam`,
`couch-fibers`) have no background to measure a rim in. Those are reported as
SKIPPED with the reason, and the summary partitions every input into outcomes
that sum to the total, so a skipped subject can never be read as a clean one.

WHAT THE SKIP TAXONOMY FOUND, AND WHAT CHANGED (V-REVIEW)
---------------------------------------------------------
Run over the 26 delivered masters this instrument measured 11 and skipped 15.
Diagnosing all guards independently rather than reporting only the first to
fire showed the 15 were not one problem but four, and that BOTH regime guards
were inert on the exact subjects they were written for:

  * REGIME GUARD 1 was written to catch `tweezers-cpl`, whose two arms are
    separate components. On these masters the tweezers segment as ONE component
    (largest share 100%, 10 components), so the guard never fires and the
    subject is measured and flagged anyway.
  * REGIME GUARD 2 was written to catch `flat-on-ruler-cpl`. It requires both
    far annuli to hold >200 px, and it splits them at a FIXED 650 px. That
    subject reaches only 599 px, so the outer annulus is EMPTY and the guard
    does not apply. It was inert on 7 of 26 subjects, including that one.

A guard that cannot apply reads exactly like a guard that passed. Both are
fixed below, and the fix for guard 2 is to split the far field at its own
MEDIAN distance so that both halves are populated whenever the far field is.

The component guard is replaced rather than loosened. Its stated concern --
that walking outward from a union of parts crosses the gaps between them -- is
answered directly by restricting every band to the DOMINANT COMPONENT'S OWN
VORONOI CELL: background whose nearest subject pixel belongs to the dominant
part. Inside that cell "outward from the silhouette" is well defined no matter
how many other parts exist, because the walk stops at the cell boundary instead
of crossing into another part's territory. This is what lets 862-component
`couch-fibers-cpl` be measured without relaxing anything.

AN ADAPTIVE FAR FIELD WAS TESTED AND REJECTED, WITH THE CALIBRATION
------------------------------------------------------------------
`112MSDCF` and `113MSDCF` have a real background -- 24% of frame -- that never
lies more than 167 and 181 px from the subject, so the fixed 400-900 px window
is unreachable and they cannot be measured. The obvious fix is a nearer far
field. It was calibrated on the 17 subjects where BOTH windows exist, by
measuring overshoot at 400-900 and again at 130-180:

    median absolute error 3318 DN, worst 13023 DN, against a 200 DN threshold.

It is not a small bias and it is not one-signed. It flips verdicts in BOTH
directions -- `dry-erase-marker-head-cpl` +236.7 -> -535.1 (HALO would become
clean) and `119MSDCF` -284.1 -> +240.5 (clean would become HALO). A far field
inside the penumbra is not a far field. Those two subjects are therefore
reported UNMEASURABLE with that reason, and the honest answer is that measuring
them needs a capture with more clearance around the subject, not a better
statistic.

MAX_SUBJ WAS A PROXY FOR TESTS THAT ARE ALREADY PRESENT
--------------------------------------------------------
"Subject is more than 80% of frame" was standing in for "there is no usable
background". That is tested directly and better by the backdrop fraction, the
far-field population and the near-band population, all of which already exist.
`coffee-bubbles` and `foam` fail those direct tests anyway (far field 0 px) and
are still UNMEASURABLE. `highly-angled-ruler-mm-cpl` fails only the proxy: it
has 106,153 far-field px and 7 populated near bands, and is now measured.
"""

import argparse
import glob
import os
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import (binary_closing, binary_opening,
                           distance_transform_edt, label)

NEAR = [(2, 6), (6, 12), (12, 20), (20, 32), (32, 50), (50, 80), (80, 120)]
FAR = (400, 900)
MIN_SUBJ = 0.02       # subject must be >=2% of frame
MAX_SUBJ = 0.80
MIN_FARPX = 20000     # need a real far field to reference against
MIN_LARGEST = 0.70    # RETIRED: replaced by the Voronoi restriction
MIN_DOM_FRAME = 0.02  # dominant part must be >=2% of FRAME to have a
                      # perimeter long enough to carry a measurable rim
MIN_BANDPX = 200      # px needed in a band before its median is used
MIN_CELL_DENS = 0.10  # stop the walk when the dominant part's cell has
                      # narrowed to <10% of its innermost density
BG_UNIFORM = 3000     # DN spread allowed between two disjoint far annuli

# THE BANDS, AND WHY NARROWING THEM WAS TRIED AND ABANDONED
# ---------------------------------------------------------
# Run on SHIP-V4 this configuration flagged six subjects, and the two that were
# checked were both confounds:
#
#   tweezers-cpl   bump 1573.7 with the non-monotonicity at d=50-80 px. The
#                  tweezers are two separate arms and walking outward from the
#                  union silhouette crosses the gap between them. Inspected at
#                  1:1: the boundary is clean.
#   flat-on-ruler  overshoot +4477 at d=80-120, profile otherwise monotone.
#                  Background brightens away from the markings to 120 px and is
#                  darker again by 400-900 px -- illumination falloff across a
#                  flat card, measured as a rim.
#
# Both violate an assumption the commission never exercised, because the
# commission used one compact blob on a uniform field.
#
# The obvious fix -- stop the bands at 24 px, where a halo physically lives,
# and reference a local far field at 32-64 -- was implemented and COMMISSIONED,
# and the commission killed it: with those bands a planted rim of 500, 1500 AND
# 4000 DN all produced bump = 0.0 and moved overshoot by 0.1 DN. The reason is
# measurable in the profile. Near the edge the subject's own penumbra rises at
# roughly 4000-5000 DN PER BAND, so a rim of a few thousand DN never breaks
# monotonicity: the artifact rides on a gradient much larger than itself. A
# radial-profile detector cannot see a rim close to a steep penumbra, and no
# amount of band tuning changes that.
#
# So the commissioned configuration is kept, and the ASSUMPTIONS ARE GUARDED
# instead. A subject that is not one compact blob on a uniform field is now
# SKIPPED with the reason printed, rather than measured by an instrument whose
# commission never covered it.


def luma(a):
    if a.ndim == 3:
        return (0.2126 * a[..., 0] + 0.7152 * a[..., 1]
                + 0.0722 * a[..., 2]).astype(np.float32)
    return a.astype(np.float32)


def otsu(v):
    h, edges = np.histogram(v, bins=256)
    h = h.astype(np.float64)
    w0 = np.cumsum(h)
    w1 = w0[-1] - w0
    mids = (edges[:-1] + edges[1:]) / 2.0
    s0 = np.cumsum(h * mids)
    s1 = s0[-1] - s0
    with np.errstate(invalid="ignore", divide="ignore"):
        m0 = s0 / w0
        m1 = s1 / w1
        var = w0 * w1 * (m0 - m1) ** 2
    var[~np.isfinite(var)] = -1
    return float(mids[int(np.argmax(var))])


def segment(y):
    t = otsu(y.ravel())
    subj = binary_opening(y < t, np.ones((3, 3)))
    subj = binary_closing(subj, np.ones((5, 5)))
    return t, subj


def profile(y, sub=4):
    """Returns (verdict, overshoot, bump, penumbra, farlevel, bands, why)."""
    y = y[::sub, ::sub]
    t, subj = segment(y)
    frac = float(subj.mean())
    if frac < MIN_SUBJ:
        return ("UNMEASURABLE", None, None, None, None, None,
                "no dark subject (%.1f%% of frame)" % (frac * 100))
    if float((y > t).mean()) < 0.05:
        return ("UNMEASURABLE", None, None, None, None, None,
                "backdrop too small (%.1f%% of frame)" % (float((y > t).mean()) * 100))

    lab, nlab = label(subj)
    if nlab < 1:
        return ("UNMEASURABLE", None, None, None, None, None, "no subject component")
    sizes = np.bincount(lab.ravel())[1:]
    dom = int(np.argmax(sizes)) + 1
    dom_frame = float(sizes[dom - 1]) / float(subj.size)
    if dom_frame < MIN_DOM_FRAME:
        return ("UNMEASURABLE", None, None, None, None, None,
                "no dominant silhouette: largest of %d parts is %.1f%% of frame "
                "(need %.0f%%)" % (nlab, dom_frame * 100, MIN_DOM_FRAME * 100))

    # THE VORONOI RESTRICTION. `ind` gives, for every background pixel, the
    # coordinates of its nearest subject pixel; the label there says which part
    # owns it. Restricting to the dominant part's cell means the outward walk
    # never crosses a gap into another part, which is precisely what REGIME
    # GUARD 1 existed to prevent -- now prevented by construction instead of by
    # refusing to measure.
    d, ind = distance_transform_edt(~subj, return_indices=True)
    d = d * sub
    own = (lab[ind[0], ind[1]] == dom) & (~subj)

    # THE FAR FIELD IS NOT RESTRICTED TO THE CELL. It is a global reference
    # level -- background far from the whole subject -- and starving it by
    # intersecting with one part's cell both broke the fibrous subjects this
    # restriction exists to rescue and shifted every already-passing subject,
    # because moving the reference moves all seven bands together. Only the
    # outward WALK has to stay inside one part's territory.
    far = (d >= FAR[0]) & (d < FAR[1])
    nfar = int(far.sum())
    if nfar < MIN_FARPX // (sub * sub):
        return ("UNMEASURABLE", None, None, None, None, None,
                "far field only %d px, need %d (subject reaches %.0f px)"
                % (nfar, MIN_FARPX // (sub * sub), float(d.max())))
    farlevel = float(np.median(y[far]))

    # REGIME GUARD 2, ALWAYS APPLICABLE. Split the far field at its OWN median
    # distance, so both halves are populated whenever the far field is. The
    # previous fixed 650 px split left the outer half empty on 7 of 26 subjects
    # -- including `flat-on-ruler-cpl`, the subject the guard was written for.
    dv = d[far]
    dmed = float(np.median(dv))
    A = far & (d < dmed)
    B = far & (d >= dmed)
    spread = None
    if int(A.sum()) > MIN_BANDPX and int(B.sum()) > MIN_BANDPX:
        spread = abs(float(np.median(y[A])) - float(np.median(y[B])))
        if spread > BG_UNIFORM:
            return ("UNMEASURABLE", None, None, None, None, None,
                    "background not uniform: far field's own halves differ by "
                    "%.0f DN (limit %d)" % (spread, BG_UNIFORM))
    else:
        return ("UNMEASURABLE", None, None, None, None, None,
                "far field cannot be split to test uniformity (%d/%d px)"
                % (int(A.sum()), int(B.sum())))

    bands = []
    dens0 = None
    for lo, hi in NEAR:
        m = own & (d >= lo) & (d < hi)
        n = int(m.sum())
        dens = n / float(hi - lo)
        if dens0 is None:
            dens0 = dens
        # CELL-PINCH TRUNCATION. Stop rather than skip: the surviving pixels
        # this far out are a directional sliver, and their median is not the
        # background level at that distance.
        if dens0 > 0 and dens / dens0 < MIN_CELL_DENS:
            bands.append((lo, hi, n, None))
            continue
        bands.append((lo, hi, n,
                      float(np.median(y[m])) - farlevel if n > MIN_BANDPX else None))
    vals = []
    for b in bands:
        if b[3] is None:
            break
        vals.append(b[3])
    if len(vals) < 3:
        return ("UNMEASURABLE", None, None, None, None, None,
                "only %d usable near band(s): dominant part's cell pinches off "
                "before a profile can be walked" % len(vals))
    over = max(vals)
    bump = 0.0
    for i in range(len(vals) - 1):
        bump = max(bump, vals[i] - vals[i + 1])
    penumbra = min(vals)
    return ("MEASURED", over, bump, penumbra, farlevel, bands, "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--only", default=None)
    ap.add_argument("--thresh", type=float, default=200.0,
                    help="DN of overshoot above far field that counts as a halo")
    ap.add_argument("--bands", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.src, "*.tif"))
                   + glob.glob(os.path.join(args.src, "*.tiff")))
    if args.only:
        files = [f for f in files if args.only in os.path.basename(f)]
    if not files:
        raise SystemExit("no masters under %s" % args.src)

    print("halo = overshoot of near-silhouette background ABOVE its own far")
    print("field, in DN of 65535. positive = bright rim = HALO.")
    print("bump = largest decrease walking outward; 0 on a monotone (clean) ramp.")
    print("penumbra = the subject's own out-of-focus transition. NOT a defect")
    print("           statistic, carries no verdict, printed to describe the picture.")
    print("threshold: halo if overshoot > %.0f DN or bump > %.0f DN\n"
          % (args.thresh, args.thresh))
    print("%-36s %10s %8s %10s %9s  %s"
          % ("subject", "overshoot", "bump", "penumbra", "farfield", "verdict"))
    print("-" * 94)

    clean = halo = unmeas = 0
    for f in files:
        stem = os.path.basename(f).split("--")[0]
        v, over, bump, pen, farl, bands, why = profile(luma(tifffile.imread(f)))
        if v == "UNMEASURABLE":
            unmeas += 1
            print("%-36s %10s %8s %10s %9s  UNMEASURABLE -- %s"
                  % (stem, "-", "-", "-", "-", why))
            continue
        if over > args.thresh or bump > args.thresh:
            halo += 1
            verdict = "*** HALO ***"
        else:
            clean += 1
            verdict = "clean"
        print("%-36s %+10.1f %8.1f %+10.1f %9.0f  %s"
              % (stem, over, bump, pen, farl, verdict))
        if args.bands:
            for lo, hi, n, dv in bands:
                print("      d %3d-%3d  n=%-8d  %s"
                      % (lo, hi, n, "%+8.1f" % dv if dv is not None else "sparse"))

    total = clean + halo + unmeas
    print("-" * 94)
    print("partition: %d clean, %d HALO, %d UNMEASURABLE, %d total (found %d)"
          % (clean, halo, unmeas, total, len(files)))
    assert total == len(files), "partition does not sum -- a subject went uncounted"
    print("An UNMEASURABLE subject is not a clean subject. It is one where the")
    print("measurement is undefined because there is no silhouette to measure")
    print("a rim against, and the reason is printed beside each.")
    return 1 if halo else 0


if __name__ == "__main__":
    sys.exit(main())
