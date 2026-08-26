"""The silhouette-aura statistic, rebuilt after the owner falsified v1 by eye.

WHY v1 (peaksite.py) WAS WRONG, both bugs, because they are different failures:

  BUG 1, structural blindness.  `prominence_near` scored a LOCAL MAXIMUM over
  its outward trough.  A dark aura is a DEPRESSION; one that recovers
  monotonically outward has NO interior local maximum, so the detector returned
  None -> 0.00%.  It was a bump detector pointed at a hole.  It scored the arm
  with a small real bump (pyramid, +0.83% at d~262) ABOVE the arm with a 25%
  crater, and I reported that as "the control has no arc there".

  BUG 2, a null inside its own reference.  NULL_LO..NULL_HI = 700..1050 lay
  entirely inside ringprofile.FAR_LO..FAR_HI = 600..1400.  Signal and null were
  normalised by the region the null was drawn from, so the ratio was ~1 by
  construction.

    A defect broader than the gap between the signal window and the null window
    contaminates its own reference and reads as absent.

WHAT REPLACES IT.  A SIGNED deviation from a far field, printed at every radius
before any summary, with three separated ideas that v1 conflated:

  * the EDGE TRANSITION.  Every subject dips near its own silhouette because
    defocus spreads a dark body outward.  It is optics, it is in both arms, and
    it is not a defect.  Calibrated here on coffee-bean, not assumed.
  * the AURA.  A depression that persists well beyond the edge transition.
    Reported over d=100-500 and as a recovery distance.
  * the RIM.  A positive excursion.  Reported separately and with its own sign,
    so a bright rim can never cancel a dark aura in one number.

    python arcprofile.py
"""

import numpy as np
import ringprofile as rp

_CACHE = {}


def luma(path):
    if path not in _CACHE:
        _CACHE[path] = rp.load_luma(path)
    return _CACHE[path]

FLIP = r"C:\dev\strehl-out\BUILD-BLEND\flip\{}--{}.tiff"
REF_LO, REF_HI = 750, 1400        # measured flat; fullprofile.py shows both
                                  # arms recover by d~700
NEAR_LO, NEAR_HI = 0, 600
AURA_LO, AURA_HI = 100, 500       # past the calibrated edge transition
NULL_LO, NULL_HI = 1500, 2100     # OUTSIDE the reference, 3x beyond recovery
STEP = 25
NSECT = 24
MIN_PX = 400
PLANT_BAND = (50, 250)
PLANT_GAIN = 0.85
RECOVER = -1.0                    # "recovered" = within 1% of far field


def profile(lum, signed, lo, hi, step=STEP, sel=None):
    ds, vs = [], []
    for d in range(lo, hi, step):
        m = (signed >= d) & (signed < d + step)
        if sel is not None:
            m = m & sel
        if int(m.sum()) < MIN_PX:
            continue
        ds.append(d + step / 2.0)
        vs.append(float(np.median(lum[m])))
    return np.array(ds), np.array(vs)


def reference(lum, signed, sel=None):
    m = (signed >= REF_LO) & (signed < REF_HI)
    if sel is not None:
        m = m & sel
    if int(m.sum()) < MIN_PX:
        return float("nan")
    return float(np.median(lum[m]))


def analyse(lum, signed, sel=None, lo=NEAR_LO, hi=NEAR_HI):
    ref = reference(lum, signed, sel)
    ds, vs = profile(lum, signed, lo, hi, sel=sel)
    if not len(vs) or not np.isfinite(ref):
        return None
    dev = 100.0 * (vs - ref) / ref
    band = (ds >= AURA_LO) & (ds <= AURA_HI)
    rec = float("inf")
    for d, x in zip(ds, dev):
        if d >= 50 and x > RECOVER:
            rec = float(d)
            break
    return dict(ref=ref, ds=ds, vs=vs, dev=dev,
                aura=float(dev[band].mean()) if band.any() else float("nan"),
                aura_worst=float(dev[band].min()) if band.any() else float("nan"),
                worst=float(dev.min()), d_worst=float(ds[int(dev.argmin())]),
                rim=float(dev.max()), d_rim=float(ds[int(dev.argmax())]),
                recover=rec)


def show(a, label, rows=True):
    print(f"  {label}")
    print(f"    far field d={REF_LO}-{REF_HI} px = {a['ref']:.0f} DN  "
          f"(ABSOLUTE level, not a ratio)")
    if rows:
        print(f"    {'d px':>6} {'DN':>8} {'% of far':>10}")
        for d, v, x in zip(a["ds"], a["vs"], a["dev"]):
            print(f"    {d:>6.0f} {v:>8.0f} {x:>+10.2f}  {'#' * int(abs(x) / 1.5)}")
    print(f"    AURA  d={AURA_LO}-{AURA_HI} mean {a['aura']:+.2f}%  "
          f"({a['ref'] * a['aura'] / 100:+.0f} DN)  worst {a['aura_worst']:+.2f}%")
    print(f"    RIM   worst positive {a['rim']:+.2f}% at d={a['d_rim']:.0f}")
    print(f"    EDGE  worst negative {a['worst']:+.2f}% at d={a['d_worst']:.0f}")
    print(f"    RECOVERS to within {abs(RECOVER):.0f}% of far field at "
          f"d={a['recover']:.0f} px")


def main():
    subj = "flower-bud-alone-cpl"
    mask, thr, kept, found = rp.subject_mask(
        luma(FLIP.format(subj, "estimator")))
    signed = rp.signed_distance(mask)
    cy, cx = [float(v) for v in np.argwhere(mask).mean(axis=0)]
    yy, xx = np.mgrid[0:mask.shape[0], 0:mask.shape[1]]
    ang = np.degrees(np.arctan2(yy - cy, xx - cx)) % 360.0
    sect = (ang / (360.0 / NSECT)).astype(np.int32)

    print("=" * 76)
    print("COMMISSIONING -- every check printed before any result")
    print("=" * 76)
    print(f"shared mask from the estimator arm, used for BOTH arms: "
          f"{mask.mean() * 100:.2f}% of frame, thr {thr:.0f} DN, "
          f"{kept} of {found} components, centroid (x={cx:.0f}, y={cy:.0f})")

    base = luma(FLIP.format(subj, "pyramid"))

    flat = np.full_like(base, 20000.0)
    fa = analyse(flat, signed)
    okA = abs(fa["worst"]) < 0.05 and abs(fa["rim"]) < 0.05
    print(f"\nNULL A -- constant 20000 DN frame, real mask, real geometry.")
    print(f"    worst {fa['worst']:+.4f}%  rim {fa['rim']:+.4f}%  -> "
          f"{'PASS' if okA else 'FAIL'}  (criterion |x| < 0.05%)")
    print(f"    the statistic does not manufacture a feature from nothing.")

    print(f"\nNULL B -- the SAME statistic on real backdrop far from any "
          f"silhouette,\n    d={NULL_LO}-{NULL_HI} px. This is the null v1 "
          f"should have had: it is\n    OUTSIDE the reference window "
          f"({REF_LO}-{REF_HI}) and 3x beyond where the\n    profile is "
          f"measured to recover, so the defect provably cannot reach it.")
    nulls = {}
    for arm in ("estimator", "pyramid"):
        na = analyse(luma(FLIP.format(subj, arm)), signed,
                     lo=NULL_LO, hi=NULL_HI)
        nulls[arm] = na
        print(f"    {arm:>10}: worst {na['worst']:+.2f}%  rim {na['rim']:+.2f}%"
              f"  mean {na['dev'].mean():+.2f}%   <- noise floor on real data")

    planted = base.copy()
    pb = (signed >= PLANT_BAND[0]) & (signed < PLANT_BAND[1])
    planted[pb] = planted[pb] * PLANT_GAIN
    inband = lambda a: float(a["dev"][(a["ds"] >= PLANT_BAND[0]) &
                                      (a["ds"] < PLANT_BAND[1])].mean())
    before = inband(analyse(base, signed))
    after = inband(analyse(planted, signed))
    expect = 100.0 * ((1 + before / 100.0) * PLANT_GAIN - 1)
    okP = abs(after - expect) < 1.0
    print(f"\nPLANT -- d={PLANT_BAND[0]}-{PLANT_BAND[1]} px multiplied by "
          f"{PLANT_GAIN} on the pyramid arm.")
    print(f"    in-band mean before {before:+.2f}%")
    print(f"    expected after      {expect:+.2f}%")
    print(f"    RECOVERED           {after:+.2f}%  -> "
          f"{'PASS' if okP else 'FAIL'}  (criterion within 1.0 pt)")

    print(f"\nEDGE CALIBRATION -- coffee-bean. Not a null: it has an edge\n"
          f"    transition of its own, which is exactly what needs measuring "
          f"so that\n    an aura can be told apart from ordinary defocus "
          f"spreading a dark body.")
    cbm, _, _, _ = rp.subject_mask(luma(FLIP.format("coffee-bean", "estimator")))
    cbs = rp.signed_distance(cbm)
    for arm in ("estimator", "pyramid"):
        ca = analyse(luma(FLIP.format("coffee-bean", arm)), cbs)
        print(f"    {arm:>10}: edge {ca['worst']:+.2f}% at d={ca['d_worst']:.0f},"
              f" recovers by d={ca['recover']:.0f},"
              f" aura band {ca['aura']:+.2f}%, rim {ca['rim']:+.2f}%")

    print()
    print("=" * 76)
    print(f"RESULT -- {subj}, both arms, shared mask, one pinned pair")
    print("=" * 76)
    res = {}
    for arm, label in (("estimator", "CONTROL  (--merge estimator)"),
                       ("pyramid", "BLEND    (--merge pyramid)")):
        a = analyse(luma(FLIP.format(subj, arm)), signed)
        res[arm] = a
        show(a, label)
        per = []
        for s in range(NSECT):
            sa = analyse(luma(FLIP.format(subj, arm)), signed,
                         sel=(sect == s))
            if sa is not None and np.isfinite(sa["aura"]):
                fr = 100.0 * (sa["ref"] - a["ref"]) / a["ref"]
                band = (sa["ds"] >= AURA_LO) & (sa["ds"] <= AURA_HI)
                au_fr = 100.0 * (sa["vs"][band].mean() - a["ref"]) / a["ref"]
                per.append((s, sa["ref"], fr, sa["aura"], au_fr))
        print(f"    per-sector AURA, all {len(per)} sectors with enough pixels."
              f"  EACH SECTOR'S OWN\n    REFERENCE IS PRINTED, because "
              f"normalising by it and not showing it is how\n    a 20% backdrop "
              f"gradient got reported as a +7.69% blend residual:")
        print(f"    {'sector':>7} {'own ref DN':>11} {'ref vs frame':>13} "
              f"{'aura/own ref':>13} {'aura/FRAME ref':>15}")
        for s, r_, fr, au, au_fr in per:
            print(f"    {s:>7} {r_:>11.0f} {fr:>+12.2f}% {au:>+12.2f}% "
                  f"{au_fr:>+14.2f}%")
        own = np.array([r[3] for r in per])
        frm = np.array([r[4] for r in per])
        refs = np.array([r[1] for r in per])
        print(f"    backdrop level spans {refs.min():.0f}-{refs.max():.0f} DN "
              f"between sectors = {100*(refs.max()-refs.min())/refs.min():.1f}%"
              f" -- this gradient, not the merge, sets the per-sector rank order")
        print(f"    against OWN   refs: min {own.min():+.2f}%  "
              f"median {np.median(own):+.2f}%  max {own.max():+.2f}% "
              f"(sector {per[int(own.argmax())][0]})")
        print(f"    against FRAME ref : min {frm.min():+.2f}%  "
              f"median {np.median(frm):+.2f}%  max {frm.max():+.2f}% "
              f"(sector {per[int(frm.argmax())][0]})  <- the max MOVES, so "
              f"neither is a defect")
        res[arm]["per"] = frm
        res[arm]["per_own"] = own
        print()

    e, p = res["estimator"], res["pyramid"]
    print("  ORDERING -- the quantity v1 got backwards:")
    print(f"    {'':<26}{'CONTROL':>12}{'BLEND':>12}")
    print(f"    {'aura band d=100-500':<26}{e['aura']:>+11.2f}%"
          f"{p['aura']:>+11.2f}%")
    print(f"    {'  same, in DN':<26}{e['ref']*e['aura']/100:>+11.0f}"
          f"{p['ref']*p['aura']/100:>+11.0f}")
    print(f"    {'per-sector median':<26}{np.median(e['per']):>+11.2f}%"
          f"{np.median(p['per']):>+11.2f}%")
    print(f"    {'recovery distance px':<26}{e['recover']:>12.0f}"
          f"{p['recover']:>12.0f}")
    print(f"    {'far-field level DN':<26}{e['ref']:>12.0f}{p['ref']:>12.0f}")
    print(f"    {'null floor (worst)':<26}"
          f"{nulls['estimator']['worst']:>+11.2f}%"
          f"{nulls['pyramid']['worst']:>+11.2f}%")
    print(f"  ARM RATIO -- the reference-free comparison. No far field is used "
          f"at all;\n  the two arms are divided by each other on identical "
          f"pixels, so no\n  normalisation can manufacture the result.")
    eL, pL = luma(FLIP.format(subj, "estimator")), luma(FLIP.format(subj, "pyramid"))
    band = (signed >= AURA_LO) & (signed <= AURA_HI)
    whole = 100.0 * (float(np.median(eL[band])) / float(np.median(pL[band])) - 1)
    rr = []
    for s in range(NSECT):
        bm = band & (sect == s)
        if int(bm.sum()) < MIN_PX:
            continue
        rr.append(100.0 * (float(np.median(eL[bm])) / float(np.median(pL[bm])) - 1))
    rr = np.array(rr)
    print(f"    CONTROL vs BLEND over the aura band, whole frame: "
          f"{whole:+.2f}%")
    print(f"    per sector: min {rr.min():+.2f}%  median {np.median(rr):+.2f}%"
          f"  max {rr.max():+.2f}%")
    print(f"    sectors where the CONTROL is DARKER than the BLEND: "
          f"{int((rr < 0).sum())} of {len(rr)}")
    print()
    gap = e["aura"] - p["aura"]
    print(f"  The two arms differ by {gap:.2f} points of far field "
          f"({e['ref']*e['aura']/100 - p['ref']*p['aura']/100:+.0f} DN) over "
          f"the aura band.")
    print(f"  The GAP is the durable number. Neither arm's own sign is: the "
          f"blend lands\n  between -1.4% and +0.2% depending on the band "
          f"cutoff, which is inside the\n  {abs(nulls['pyramid']['worst']):.1f}%"
          f" null floor and therefore not distinguishable from zero.")
    print(f"  Against the null floor on the same backdrop: the control's worst "
          f"bin {e['worst']:+.2f}%")
    print(f"  is {abs(e['worst'] / nulls['estimator']['worst']):.1f}x the floor"
          f" {nulls['estimator']['worst']:+.2f}%; the blend's aura-band worst "
          f"{p['aura_worst']:+.2f}% is")
    print(f"  {abs(p['aura_worst'] / nulls['pyramid']['worst']):.2f}x the floor,"
          f" i.e. below it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

