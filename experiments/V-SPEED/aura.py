"""Measure a dark aura ring without a far-field reference and without caring
about the penumbra.

WHY NOT `halo_profile.py`'s STATISTICS
--------------------------------------
`overshoot = max(band_median) - median(far field at 400-900 px)` has two
properties this lane measured today and neither is survivable:

  * On all 11 subjects that instrument scores, the argmax is the OUTERMOST
    band (80-120 px). It is never reading an interior feature, so it is not
    reading a rim at any distance -- it is reading the background's own level
    at 120 px against its level at 900 px.
  * Consequently the verdict moves with the reference. `dry-erase-marker-head`
    reads +236.7 (HALO) against 400-900 and -325.7 (clean) against 120-250.
    A rim four pixels from a silhouette cannot know where the reference
    annulus is.

And `penumbra`, the statistic that instrument prints but explicitly refuses to
score, is the same quantity in which this project's ONLY quantified halo lives:
`stack --help` records the estimator backend's aura on `flower-bud-alone-cpl`
as "the backdrop sits 4739 DN BELOW its own far field across the 80-200 px aura
zone; the pyramid sits 166 DN below". Below. The defect is a DARK aura, and the
instrument looks for a bright rim.

WHAT THIS MEASURES INSTEAD
--------------------------
A penumbra is a monotone recovery: walking outward from a dark subject the
background rises smoothly to its own level. A background illumination gradient
is also monotone, in whichever direction the lighting falls. An AURA is neither
-- it is a local DIP, a ring darker than both the ring inside it and the ring
outside it.

So fit the radial profile with the best monotone NON-DECREASING function
(pool-adjacent-violators), and separately with the best monotone
NON-INCREASING one, and take the smaller of the two shortfalls.

THAT DESIGN WAS BUILT, COMMISSIONED AND KILLED. Recorded because the reason
generalises. A monotone fit through a dip POOLS the dip with its neighbours, so
the fit itself sags into the feature it is supposed to reference: a planted
3000 DN ring on flat ground read **1208.8**, and the same ring on a steep
penumbra read **0.0**. A baseline estimated from data that includes the defect
is dragged toward the defect, and the error is in the direction that hides it.

WHAT IS MEASURED INSTEAD: VALLEY PROMINENCE
-------------------------------------------
For each interior band `i`, the two shoulders are the highest levels reached
anywhere inside and anywhere outside it, and the depth is how far the band sits
below the LOWER of those two:

    depth_i = min( max(v[:i]), max(v[i+1:]) ) - v[i]
    aura    = max(0, max_i depth_i)

The shoulders are taken from data strictly excluding band `i`, so the reference
cannot sag into the feature. Trend immunity is by construction and needs no
tuning:

  * monotone rising  -> max(v[:i]) = v[i-1] < v[i], every depth negative, 0.
  * monotone falling -> max(v[i+1:]) < v[i], every depth negative, 0.
  * a genuine dip    -> both shoulders above it, and the full depth is
    recovered rather than a fraction of it.

`rim`, the same statistic on the negated profile, measures a BRIGHT ring on the
same footing, so both signs of the defect come from one instrument.

Three things follow that the reference-based statistic cannot claim:

  * No far field is used, so there is nothing for the reference distance to
    change.
  * The penumbra is monotone and scores zero, so a ring close to a steep
    penumbra is still visible -- the failure `halo_profile.py`'s header calls
    structural for a radial-profile detector ("a radial-profile detector cannot
    see a rim close to a steep penumbra, and no amount of band tuning changes
    that") is a property of differencing against a far field, not of radial
    profiles.
  * It has a known and measured sensitivity FLOOR rather than an unknown bias:
    where the penumbra is still climbing through the ring, the inner shoulder
    is itself depressed and the recovered depth understates the plant. Plant 5
    measures that fraction rather than assuming it away. Understating a defect
    is the safe direction for a detector; it can miss one, but it cannot
    manufacture one.

COMMISSIONING
-------------
Run with `--commission`. Five plants, and they are chosen so that passing them
by accident is hard:

  1. planted dark ring of known depth  -> must be recovered near that depth
  2. planted bright ring of known height -> must be recovered by `rim`
  3. no plant on a synthetic monotone penumbra -> must read 0
  4. planted monotone background GRADIENT -> must read 0. This is the confound
     that produces three of ORCH's four HALO verdicts; if this instrument
     scores a gradient it inherits the same defect.
  5. planted ring on top of a steep penumbra -> must still be DETECTED well
     clear of the 200 DN verdict threshold, and the recovered fraction is
     printed. This is the case the previous instrument declares impossible, so
     it is the one that decides whether this design is worth anything.
"""
import argparse
import glob
import json
import os
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import (binary_closing, binary_opening,
                           distance_transform_edt)

OUT = pathlib.Path(r"C:\dev\strehl-out\V-SPEED-HALO")
CACHE = OUT / "cache"
SUB = 4

# Finer and further than halo_profile.py's seven bands: the estimator aura is
# documented at 80-200 px and the tweezers dip sits at 50-80, so the profile
# has to extend past both with enough resolution to localise a ring.
EDGES = [2, 4, 6, 9, 12, 16, 20, 26, 32, 40, 50, 62, 80, 100, 120,
         150, 185, 230, 280, 340, 420]
MIN_N = 200

# Bands closer than this to the subject are shoulders only, never the
# reported extremum. See deficit() for the measurement that set it: the 5-20
# px zone carries a one-band penumbra-transition wiggle on most subjects, and
# the defect under investigation is a broad 50-300 px feature. 30 px sits
# above the wiggle and below every documented aura.
MIN_PX = 30.0

# Verdict gates. See verdict() for where each comes from.
HALO_DN = 200.0
HALO_W = 120.0
HALO_MAX_PX = 200.0
HALO_FIELD_FRAC = 0.5


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
    s = y < t
    s = binary_opening(s, np.ones((3, 3)))
    s = binary_closing(s, np.ones((5, 5)))
    return s


def prominence(v):
    """Per-band valley depth below the lower of its two outer shoulders.

    The shoulders exclude band `i` itself, which is the whole point: a
    baseline estimated from data containing the defect sags into it. Returns
    the per-band depths, negative where the profile is merely monotone.
    """
    v = np.asarray(v, float)
    n = len(v)
    d = np.full(n, -np.inf)
    for i in range(1, n - 1):
        d[i] = min(v[:i].max(), v[i + 1:].max()) - v[i]
    return d


def width_px(v, mids, i, p, sign=+1):
    """Full width of the feature at band i, at half its prominence, in px.

    THIS IS THE DISCRIMINATOR THAT SEPARATES A HALO FROM A LIGHTING GRADIENT,
    and it is the second confound this instrument had to grow past.
    `prominence` is immune to a MONOTONE background trend by construction, and
    plant 4 proves it. It is NOT immune to a broad ARCH -- a background that
    rises across the field and then falls has a genuine interior maximum, and
    the instrument was reading that maximum as a bright ring.

    Measured on the faithful corpus, this is exactly what the two loudest
    "rim" scores were. `flat-on-ruler-cpl` rises smoothly 37317 -> 50604 DN
    from 5 px to 168 px and falls to 45024 by 255 px; `lavendar-cpl` rises
    41972 -> 51650 from 5 px to 110 px and falls to 46937 by 310 px. Both are
    single arches spanning the whole measured field with no narrow feature
    anywhere. Their 5579 DN and 4713 DN "rims" are the height of the arch.

    A halo is narrow and sits against the subject: on `tweezers-cpl` the
    bright peak at 36 px and the dark trough at 56 px are 20 px apart. So
    width, not amplitude, is what tells them apart, and amplitude alone will
    convict a lighting gradient every time.
    """
    v = np.asarray(v, float) * sign
    mids = np.asarray(mids, float)
    if p <= 0:
        return 0.0
    half = v[i] - p / 2.0
    # Crossings are INTERPOLATED between band midpoints, not snapped to them.
    # Snapping gave a 45 px top-hat ring that occupies a single band a width
    # of 0.0 px, because the first band on each side was already below half
    # prominence -- so the narrowest possible real feature scored the same as
    # no feature at all, and a width threshold built on it would have passed
    # everything.
    lo = i
    while lo > 0 and v[lo - 1] > half:
        lo -= 1
    if lo == 0:
        xl = mids[0]
    else:
        a, b = v[lo - 1], v[lo]
        t = (half - a) / (b - a) if b != a else 0.0
        xl = mids[lo - 1] + t * (mids[lo] - mids[lo - 1])
    hi = i
    while hi < len(v) - 1 and v[hi + 1] > half:
        hi += 1
    if hi == len(v) - 1:
        xr = mids[-1]
    else:
        a, b = v[hi], v[hi + 1]
        t = (a - half) / (a - b) if a != b else 0.0
        xr = mids[hi] + t * (mids[hi + 1] - mids[hi])
    return float(xr - xl)


def deficit(v, mids=None, min_px=0.0):
    """Depth of the darkest ring, and which band carries it.

    `min_px` excludes bands closer to the subject than that from being the
    EXTREMUM, while leaving them available as shoulders. This is not
    cosmetic. Measured on the faithful corpus: 14 of 26 subjects returned
    aura == rim to 0.1 DN, and the profiles showed why. `bee-1-cpl` rises
    monotonically 40281 -> 58863 DN from 5 px to 310 px with exactly one
    exception, a single band at 14 px sitting 813 DN below its neighbour at
    10 px. A one-band wiggle of amplitude A is BOTH a valley of depth A (read
    at the lower band) and a peak of height A (read at the upper one), so one
    feature was being reported twice under two names with the same number.

    That feature is also the wrong feature. It sits in the 5-20 px
    subject-edge transition, where the penumbra is steep and a band boundary
    landing mid-slope produces a wiggle of exactly this size. The defect the
    owner complains about is broad: the project's own quantified example is an
    aura "across the 80-200 px zone" (stack --help, on flower-bud-alone-cpl).
    So the headline restricts to d >= min_px and the edge zone is reported
    separately rather than deleted -- a number moved out of the headline still
    has to be visible, or the exclusion is just a way of not seeing it.
    """
    d = prominence(v)
    if mids is not None and min_px > 0:
        d = np.where(np.asarray(mids, float) >= min_px, d, -np.inf)
    if not np.any(np.isfinite(d)):
        return 0.0, 0
    i = int(np.argmax(d))
    return max(0.0, float(d[i])), i


def surplus(v, mids=None, min_px=0.0):
    """The same, for a BRIGHT ring."""
    return deficit(-np.asarray(v, float), mids, min_px)


def radial(y, subj, scale=SUB):
    """Median luma in each distance band.

    `scale` converts the array's own pixel spacing into sensor pixels. It is
    explicit because getting it wrong is silent and total: `main` feeds this a
    4x subsampled master and needs scale=4, while `commission` feeds it a
    full-resolution synthetic and needs scale=1. Defaulting to SUB for both
    put every planted ring 4x further out than its band label, so a 3000 DN
    plant at d=167 was looked for at d=670, fell off the end of EDGES, and
    read a clean 0.0 -- an instrument that reports "no defect" for a defect it
    was pointed away from.
    """
    d = distance_transform_edt(~subj) * scale
    mids, meds, ns = [], [], []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        m = (d >= lo) & (d < hi)
        n = int(m.sum())
        if n < MIN_N:
            continue
        mids.append(0.5 * (lo + hi))
        meds.append(float(np.median(y[m])))
        ns.append(n)
    return np.array(mids), np.array(meds), np.array(ns, float)


def measure(y, subj, scale=SUB, min_px=MIN_PX):
    mids, meds, ns = radial(y, subj, scale)
    if len(meds) < 5:
        return None
    au, ai = deficit(meds, mids, min_px)
    ri, rj = surplus(meds, mids, min_px)
    eau, eai = deficit(meds)
    eri, erj = surplus(meds)
    aw = width_px(meds, mids, ai, au, sign=-1)
    rw = width_px(meds, mids, rj, ri, sign=+1)
    return {"aura_dn": round(au, 1), "rim_dn": round(ri, 1),
            "aura_at_px": float(mids[ai]), "rim_at_px": float(mids[rj]),
            "aura_w_px": round(aw, 1), "rim_w_px": round(rw, 1),
            "edge_aura_dn": round(eau, 1), "edge_rim_dn": round(eri, 1),
            "edge_aura_at_px": float(mids[eai]),
            "min_px": min_px, "nbands": len(meds),
            "field_px": float(mids[-1]),
            "mids": [float(x) for x in mids],
            "meds": [round(float(x), 1) for x in meds]}


# ---------------------------------------------------------------- commission

def synth(penumbra=0.0, gradient=0.0, ring=0.0, ring_at=167.5, ring_w=45.0,
          sigma=None, size=1400, rad=220, arch=0.0):
    """A synthetic subject: dark disc, bright ground, optional features.

    The ring is a TOP HAT by default, not a Gaussian. A Gaussian ring is
    smeared by the band medians that sample it, so a planted 3000 DN ring
    reads 2485 and the instrument looks 17% biased when the shortfall is
    entirely in the plant. A top hat wider than the bands has a flat bottom
    that the band median reproduces exactly, which makes plant 1 an accuracy
    test rather than a convolution test. `sigma` restores the Gaussian for the
    sensitivity sweep, where a controllable slope is the point.

    THE DEFAULT GEOMETRY IS NOT ARBITRARY. `ring_at=167.5, ring_w=45` places
    the ring over d=145..190, which strictly contains the band d=150..185, so
    exactly one band median lands wholly inside the ring and reads the planted
    depth. The first attempt used 150 +- 15, which straddled the 150 boundary
    and left the ring occupying half of each neighbouring band: the plant was
    3000 DN deep and the instrument correctly read 0.0, because no band median
    was ever inside it. Plant geometry has to match partition geometry by
    construction, or a commission failure means nothing about the instrument.
    """
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.hypot(yy - size / 2.0, xx - size / 2.0)
    y = np.full((size, size), 40000.0, np.float32)
    y[r < rad] = 2000.0
    d = r - rad
    out = d > 0
    if penumbra:
        y[out] -= penumbra * np.exp(-d[out] / 45.0)
    if gradient:
        y[out] -= gradient * (1.0 - np.clip(d[out] / 600.0, 0, 1))
    if arch:
        # A background that RISES across the field and then FALLS. This is the
        # confound `width_px` exists to reject: it has a genuine interior
        # maximum, so no trend-immunity argument disposes of it, and on the
        # real corpus it is the largest "rim" score there is.
        #
        # It peaks at d=200 px, comfortably inside the profile. The first
        # version peaked at d=350, which landed in the OUTERMOST band -- and
        # `prominence` never scores an endpoint, because an endpoint has no
        # outer shoulder. So the arch read 0 DN and the plant tested nothing.
        y[out] += arch * np.sin(np.pi * np.clip(d[out] / 400.0, 0, 1))
    if ring:
        if sigma:
            y[out] -= ring * np.exp(-((d[out] - ring_at) ** 2) / (2 * sigma ** 2))
        else:
            band = out & (np.abs(d - ring_at) <= ring_w / 2.0)
            y[band] -= ring
    return y.astype(np.float32)


def commission():
    ok, fail = 0, []

    def check(name, y, key, want, tol):
        nonlocal ok
        subj = y < 20000
        r = measure(y, subj, scale=1)
        got = r[key]
        good = abs(got - want) <= tol
        print("  [%s] %-46s %s=%8.1f  want %7.1f +-%.0f"
              % ("PASS" if good else "FAIL", name, key, got, want, tol))
        if good:
            ok += 1
        else:
            fail.append(name)
        return r

    print("commissioning aura.py -- eight plants, both signs\n")
    check("1. dark ring 3000 DN on flat ground",
          synth(ring=3000.0), "aura_dn", 3000.0, 400.0)
    check("2. bright ring 3000 DN on flat ground",
          synth(ring=-3000.0), "rim_dn", 3000.0, 400.0)
    check("3. penumbra only, no ring (must read zero)",
          synth(penumbra=18000.0), "aura_dn", 0.0, 60.0)
    check("4. monotone background gradient 6000 DN (the confound)",
          synth(gradient=6000.0), "aura_dn", 0.0, 60.0)

    # Plant 5 is a SENSITIVITY measurement, not an accuracy one. Where the
    # penumbra is still climbing through the ring the inner shoulder is itself
    # depressed, so the recovered depth understates the plant by a fraction
    # this prints rather than assumes. What must hold is DETECTION, clear of
    # the 200 DN verdict threshold.
    y5 = synth(penumbra=18000.0, ring=3000.0)
    r5 = measure(y5, y5 < 20000, scale=1)
    got5 = r5["aura_dn"]
    good5 = got5 >= 1000.0
    print("  [%s] %-46s aura_dn=%8.1f  want >=1000 (detection)"
          % ("PASS" if good5 else "FAIL",
             "5. dark ring 3000 DN ON a steep 18000 DN penumbra", got5))
    if good5:
        ok += 1
    else:
        fail.append("5. ring on steep penumbra")
    print("        recovery on a steep penumbra: %.0f%% of the planted 3000 DN"
          % (100.0 * got5 / 3000.0))

    # Plant 6 commissions the MIN_PX exclusion itself, in both directions.
    # A ring planted inside the excluded edge zone must vanish from the
    # headline AND still be visible in the edge channel. Testing only the
    # first half would be satisfied by an exclusion implemented as "return
    # zero always"; testing only the second would be satisfied by an
    # exclusion that never excludes. Both halves, or the knob is unproven.
    y6 = synth(ring=3000.0, ring_at=14.0, ring_w=8.0)
    r6 = measure(y6, y6 < 20000, scale=1)
    head6, edge6 = r6["aura_dn"], r6["edge_aura_dn"]
    good6 = (head6 <= 200.0) and (edge6 >= 1000.0)
    print("  [%s] %-46s head=%7.1f edge=%7.1f  want head<=200 AND edge>=1000"
          % ("PASS" if good6 else "FAIL",
             "6. ring INSIDE the excluded edge zone (d=14 px)", head6, edge6))
    if good6:
        ok += 1
    else:
        fail.append("6. edge-zone exclusion")

    # Plant 7 commissions the WIDTH discriminator, which is the only thing
    # separating a halo from a lighting gradient. Both arms carry the SAME
    # 3000 DN amplitude, so amplitude cannot pass this test -- only width can.
    # Reporting a width without checking it against a broad plant would leave
    # the possibility that the number is real but never large.
    y7a = synth(ring=-3000.0)                    # narrow ring, 45 px wide
    r7a = measure(y7a, y7a < 20000, scale=1)
    y7b = synth(arch=3000.0)                     # broad arch, ~266 px wide
    r7b = measure(y7b, y7b < 20000, scale=1)
    # The gates come from the plants' ANALYTIC widths, not from what the first
    # run happened to print. The ring is a 45 px top hat. The arch is
    # sin(pi*d/400), which crosses half amplitude at d=66.7 and d=333.3, so
    # its true half-prominence width is 266.7 px. Band discretisation costs a
    # few percent of that. Setting the gate to whatever the run produced would
    # make this plant a tautology, so each side is allowed a wide tolerance
    # and the claim that actually matters -- that the two are far apart -- is
    # tested as a RATIO, which no single-sided tuning can fake.
    narrow, broad = r7a["rim_w_px"], r7b["rim_w_px"]
    sep = broad / narrow if narrow > 0 else 0.0
    good7 = (narrow <= 90.0) and (broad >= 200.0) and (sep >= 3.0)
    print("  [%s] %-46s narrow=%6.1f px broad=%6.1f px  ratio %.1fx"
          % ("PASS" if good7 else "FAIL",
             "7. width separates a ring from a lighting arch",
             narrow, broad, sep))
    print("        analytic widths 45.0 and 266.7 px; gates <=90, >=200, >=3x")
    print("        both plants carry the same 3000 DN planted amplitude and read")
    print("        %.0f and %.0f DN, so amplitude CANNOT separate them -- only width."
          % (r7a["rim_dn"], r7b["rim_dn"]))
    if good7:
        ok += 1
    else:
        fail.append("7. width discriminator")

    # Plant 8 commissions the field-fraction guard as coded: the SAME ring, in
    # the SAME small field, at two positions either side of the boundary. It
    # tests the implemented behaviour and claims nothing more. The choice of
    # 0.5 rests on the argument in verdict() -- a prominence is a height above
    # two shoulders, and the outer shoulder of a feature at 67% of the field
    # is measured over the remaining third, which in a real frame is its
    # vignetted corners -- plus the two corpus subjects that showed it.
    # An inert guard passes the first arm; an over-eager one fails the second.
    y8 = synth(ring=-3000.0, ring_at=207.5, ring_w=55.0, size=700, rad=220)
    r8 = measure(y8, y8 < 20000, scale=1)
    v8 = verdict(r8)
    y8b = synth(ring=-3000.0, ring_at=90.0, ring_w=30.0, size=700, rad=220)
    r8b = measure(y8b, y8b < 20000, scale=1)
    v8b = verdict(r8b)
    good8 = (not v8.startswith("HALO")) and v8b.startswith("HALO")
    print("  [%s] %-46s outer=%-12s inner=%-12s"
          % ("PASS" if good8 else "FAIL",
             "8. field-fraction guard fires only outside it", v8, v8b))
    print("        same 3000 DN ring, same %.0f px field: at %.0f px (%.0f%%)"
          % (r8["field_px"], r8["rim_at_px"],
             100.0 * r8["rim_at_px"] / r8["field_px"]))
    print("        reads %.0f DN and is rejected; at %.0f px (%.0f%%) it reads"
          % (r8["rim_dn"], r8b["rim_at_px"],
             100.0 * r8b["rim_at_px"] / r8b["field_px"]))
    print("        %.0f DN and is kept. Amplitude is equal; only position differs."
          % r8b["rim_dn"])
    if good8:
        ok += 1
    else:
        fail.append("8. field-fraction guard")

    # THE SENSITIVITY ENVELOPE, printed rather than claimed.
    #
    # This design does not escape the limit `halo_profile.py`'s header states.
    # A dip detector needs a local minimum, and a ring whose own slope is
    # gentler than the penumbra it sits on produces an inflection instead --
    # the profile shelves but never turns over. That first cost this lane a
    # failed commission: a Gaussian ring of sigma 18 at d=60 on an 18000 DN
    # penumbra read exactly 0.0, because at d=60 the penumbra falls ~105 DN/px
    # and the ring's steepest flank is about the same.
    #
    # So the honest deliverable is not "it sees rings"; it is the boundary
    # between the rings it sees and the ones it cannot. Sweeping ring width at
    # fixed depth measures exactly that, and the widest detected width is a
    # number a reader can check a real feature against.
    print("\n  sensitivity envelope. Two different limits, measured not claimed.")
    print("  (a) DEPTH floor: band-aligned top-hat ring on the 18000 DN")
    print("      penumbra, depth swept. Below some depth it is not detectable.")
    print("    %10s %10s %10s" % ("planted DN", "aura DN", "verdict"))
    env = []
    for dn in [3000, 1500, 750, 375, 200, 100]:
        ys = synth(penumbra=18000.0, ring=float(dn))
        rs = measure(ys, ys < 20000, scale=1)
        env.append({"kind": "depth", "planted": dn, "aura": rs["aura_dn"]})
        print("    %10d %10.1f %10s"
              % (dn, rs["aura_dn"],
                 "detected" if rs["aura_dn"] > 200 else "MISSED"))
    print("  (b) SHAPE blind spot: a ring gentler than the penumbra it sits on")
    print("      shelves the profile instead of turning it over, and no dip")
    print("      detector can see it. This is the limit halo_profile.py's")
    print("      header calls structural, and this design does NOT escape it.")
    print("    %8s %8s %10s %10s" % ("sigma px", "at d px", "aura DN", "verdict"))
    for sg, at in [(4, 60), (12, 60), (18, 60), (18, 150), (30, 150)]:
        ys = synth(penumbra=18000.0, ring=3000.0, ring_at=at, sigma=sg)
        rs = measure(ys, ys < 20000, scale=1)
        env.append({"kind": "shape", "sigma": sg, "at": at,
                    "aura": rs["aura_dn"]})
        print("    %8d %8d %10.1f %10s"
              % (sg, at, rs["aura_dn"],
                 "detected" if rs["aura_dn"] > 200 else "MISSED"))
    print("  Read both as the instrument's blind spots, not as corpus results.")
    (OUT / "aura-envelope.json").write_text(json.dumps(env, indent=1))

    print("\ncommission: %d/8 %s" % (ok, "PASS" if not fail else "FAIL"))
    if fail:
        print("failed: " + ", ".join(fail))
    return not fail


def verdict(r):
    """HALO only if a feature is both LARGE ENOUGH and NARROW ENOUGH.

    THRESHOLD PROVENANCE, because a threshold with no provenance is an
    opinion. The amplitude gate of 200 DN is halo_profile.py's, kept
    deliberately so the two instruments' verdicts differ only by what they
    measure and not by where they cut. The width gate of 120 px comes from
    plant 7: a 45 px ring reads 36 px and a 267 px lighting arch reads 243 px,
    so anything between 90 and 200 separates them, and 120 is the midpoint of
    that interval. It is also above the widest real halo in the corpus -- the
    tweezers-cpl peak at 36 px and trough at 56 px are 20 px apart -- and
    below the narrowest lighting arch.

    The DISTANCE cap of 200 px is the project's own number, not a new one:
    `strehl stack --help` quantifies the estimator's aura as sitting "across
    the 80-200 px aura zone" on flower-bud-alone-cpl. A feature beyond that is
    not adjacent to the subject and is the background's business. Without this
    cap the verdict convicted `lavendar-cpl` and `flat-on-ruler-cpl` on a
    shallow far-field wiggle at 310 px and 255 px in a 380 px field, which is
    the same confound the width gate was added to defeat, merely relocated.

    The FIELD-FRACTION guard is the third and last confound. A prominence is a
    height above two shoulders, so it means nothing when one shoulder is the
    edge of the measured field. `112MSDCF` and `113MSDCF` have small
    backgrounds -- 14 and 15 bands, reaching only 135 px -- and both rise
    smoothly from 26670 DN at 5 px to 47752 DN at 90 px and fall away again.
    That is the same lighting arch as `lavendar-cpl`, but because the field
    ends at 135 px the arch is cut off before it can look broad, and it scored
    the two largest "rims" in the corpus at 8680 and 8469 DN with a width of
    only 64 px. Requiring the feature to sit inside the inner half of the
    field means there is at least as much profile beyond it as before it, so
    "narrow" is a measurement rather than an artifact of running out of
    background. tweezers-cpl sits at 56 px of 380 (0.15); those two sat at 90
    px of 135 (0.67).
    """
    a, aw, aat = r["aura_dn"], r["aura_w_px"], r["aura_at_px"]
    b, bw, bat = r["rim_dn"], r["rim_w_px"], r["rim_at_px"]
    dark = (a >= HALO_DN and aw <= HALO_W and aat <= HALO_MAX_PX
            and aat <= HALO_FIELD_FRAC * r["field_px"])
    bright = (b >= HALO_DN and bw <= HALO_W and bat <= HALO_MAX_PX
              and bat <= HALO_FIELD_FRAC * r["field_px"])
    broad = ((a >= HALO_DN and not dark) or (b >= HALO_DN and not bright))
    if dark and bright:
        return "HALO pair"
    if dark:
        return "HALO dark"
    if bright:
        return "HALO bright"
    if broad:
        return "gradient"
    return "clean"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?",
                    default=r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful")
    ap.add_argument("--commission", action="store_true")
    ap.add_argument("--tag", default="faithful")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    if args.commission:
        return 0 if commission() else 1
    if not commission():
        print("\nrefusing to measure with an uncommissioned instrument")
        return 1

    files = sorted(glob.glob(os.path.join(args.src, "*.tif"))
                   + glob.glob(os.path.join(args.src, "*.tiff")))
    if args.only:
        files = [f for f in files if args.only in os.path.basename(f)]

    rows = []
    print("\n\naura = depth of the darkest ring, rim = height of the brightest,")
    print("both reference-free. w = full width at half prominence.")
    print("A HALO is NARROW and sits near the subject. A broad feature is the")
    print("background's own lighting arch, and amplitude cannot tell them")
    print("apart -- only width can. See width_px() and plant 7.\n")
    print("%-38s %8s %6s %5s %8s %6s %5s %s"
          % ("subject", "aura", "w px", "@px", "rim", "w px", "@px", "verdict"))
    print("-" * 96)
    for f in files:
        stem = os.path.basename(f).split(".")[0]
        y = luma(tifffile.imread(f))[::SUB, ::SUB]
        r = measure(y, segment(y))
        if r is None:
            print("%-38s %8s %6s %5s %8s %6s %5s %s"
                  % (stem, "-", "-", "-", "-", "-", "-", "too few bands"))
            continue
        r["subject"] = stem
        r["verdict"] = verdict(r)
        rows.append(r)
        print("%-38s %8.1f %6.0f %5.0f %8.1f %6.0f %5.0f %s"
              % (stem, r["aura_dn"], r["aura_w_px"], r["aura_at_px"],
                 r["rim_dn"], r["rim_w_px"], r["rim_at_px"], r["verdict"]))
    print("-" * 96)
    halos = [r for r in rows if r["verdict"].startswith("HALO")]
    grads = [r for r in rows if r["verdict"] == "gradient"]
    halos.sort(key=lambda r: -max(r["aura_dn"], r["rim_dn"]))
    print("%d HALO, %d gradient-only, %d clean, %d scored, %d files"
          % (len(halos), len(grads),
             len(rows) - len(halos) - len(grads), len(rows), len(files)))
    if halos:
        print("worst: " + ", ".join(
            "%s %.0f DN at %.0f px" % (r["subject"],
                                       max(r["aura_dn"], r["rim_dn"]),
                                       r["aura_at_px"])
            for r in halos[:5]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("aura-%s.json" % args.tag)).write_text(json.dumps(rows, indent=1))
    print("wrote %s" % (OUT / ("aura-%s.json" % args.tag)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
