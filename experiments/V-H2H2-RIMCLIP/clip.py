"""CLIPPING, free field: strehl vs enfuse vs focus-stack.

THE FIRST RESULT IS THAT THE QUESTION AS POSED HAS A NULL ANSWER.  recon.py
measured the container ceiling on every arm of both subjects:

    subject 113   strehl 0.0003%   enfuse 0.0005%   fs15 0.0004%
    subject 119   strehl 0.0000%   enfuse 0.0000%   fs15 0.0000%

NOBODY CLIPS.  The README's headline clipping win -- "the fork clips 32% of the
frame on one subject; strehl clips 4e-6" -- is a property of the PREDECESSOR's
Lightroom pipeline, not of focus-stack's merge, and IT DOES NOT TRANSFER TO THE
FREE FIELD.  Here every arm is fused from strehl's own `--linear-srgb
--demosaic` TIFFs, so the exposure that blew that background never happens.
That is a retraction of a comparison, not a loss on one.

SO THE GAUGE ESCALATES from "does it hit the ceiling" to "does it destroy
detail in the extreme zones", which is the thing clipping was standing in for.

A GAUGE THAT CANNOT BE MOVED BY A TONE CURVE.  Two of the three arms in the
wider project carry content-derived tone curves, and a ratio computed across
two different curves measures the curves.  So the zone is defined by RANK --
the top and bottom k% of an arm's own pixels, by its own order -- and the
statistic is the fraction of those pixels whose 3x3 neighbourhood has ZERO
RANGE.  A strictly monotone map preserves both rank order and equality, so both
the zone and the statistic are invariant under any such map by construction.

INVARIANCE IS NOT ENOUGH ON ITS OWN.  A statistic that never moves is invariant
under every map including the ones that should move it, and would pass the
invariance test perfectly by being blind.  So a NON-MONOTONE map is run too,
and it must change the reading.  Invariance is only evidence when paired with
demonstrated power.

THE FOOLING DIRECTION, AND IT FAVOURS THE COMPARATORS.  Noise breaks ties, so a
NOISIER arm has fewer flat neighbourhoods and scores BETTER on this gauge for
no merit.  V-NOISE2 measured the comparators noisier than strehl by 1.54x-3.54x,
so the bias runs AGAINST this project, and a noise ladder is run to size it.

THE CONTAINER CONFOUND, WHICH IS LARGER THAN THE EFFECT.  focus-stack writes
8-BIT.  recon.py measured its top 1% using 146 distinct values on 113 against
strehl's 7226, and its bottom 1% using 2 against strehl's 134.  An 8-bit
container ties pixels wholesale, so fs15 is charged for its container rather
than its merge.  Every comparison including fs15 is therefore reported
CONTAINER-MATCHED, with all arms requantised to 8 bits, and the 16-bit
strehl-vs-enfuse comparison is reported separately.  A quantisation ladder
(16, 14, 12, 10, 8 bits) sizes what the container alone is worth.

THE FIRST VERSION OF THIS FILE FAILED, AND THE FAILURE IS KEPT HERE.
Its noise ladder ran at NATIVE bit depth, where a 3x3 zero-range test on
16-bit float data reads 0.000% no matter what noise is added -- nothing is
ever exactly equal.  The VERDICT, however, was computed on the 8-bit
container-matched images, where the same statistic reads tens of percent.
The control and the measurement were in DIFFERENT REGIMES, so the ladder
reported "0.0000 pts" for a confound that was in fact worth 41 points, and
the run duly declared:

    enfuse    highlight  -41.4448 pts   noise ladder 0.0000 pts  => STREHL WORSE
    fs15-coh  highlight  -41.4421 pts   noise ladder 0.0000 pts  => STREHL WORSE

The decisive control, run afterwards, disposed of it completely.  Raising
strehl to enfuse's measured sigma and THEN quantising:

    strehl as-is                      highlight 41.760%   shadow 65.376%
    strehl + noise to enfuse sigma    highlight  0.902%   shadow  1.348%
    enfuse, measured                  highlight  0.315%   shadow 49.590%

The 41 points were NOISE BREAKING TIES, not destroyed detail.  strehl's
sigma is 0.29 of an 8-bit level on this subject and enfuse's is 0.56, so
strehl's neighbours land on the same level and enfuse's straddle two.  The
gauge was charging the QUIETER arm for being quieter -- penalising it on
exactly the axis V-NOISE2 measured it winning.  A control that cannot move
in the regime where the verdict is computed is not a control; it is a
statement about the regime it was run in.

SO BOTH FIXES ARE STRUCTURAL, not tuning.  Every commissioning arm now runs
through the SAME `prep` the measurement runs through, and the arms are
NOISE-MATCHED to the noisiest arm before the container is matched, so that
neither the container nor the noise is what is being compared.

AND THE IMPROVEMENT ARM WAS TOO EASY.  `0.5*clipped + 0.5*original` is a
strictly monotone function of the original, so a rank-invariant statistic is
GUARANTEED to return to its base reading on it -- the arm passed by
construction and demonstrated nothing.  A second improvement arm now
restores detail in a random half of the BLOCKS, which is a spatial choice
and therefore not a pointwise map at all; a rank-invariant statistic has no
obligation to move on it, so its movement is evidence.

INVOCATION (rule 47).  Reads the arm files named by V-NOISE2/hd2.py.  Writes
C:\\dev\\strehl-out\\V-H2H2\\rimclip\\clip-<key>.json and prints everything.

    python clip.py [113|119 ...]
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import ffarms                                                    # noqa: E402

OUT = r"C:\dev\strehl-out\V-H2H2\rimclip"
BLK = 256
ZONE_PCT = 1.0


def _blocks(shape, b=BLK):
    h, w = shape
    return [(y, x) for y in range(0, h - b + 1, b)
            for x in range(0, w - b + 1, b)]


def plateau(g, pct=ZONE_PCT, blocks=None):
    """Fraction of extreme-zone pixels whose 3x3 neighbourhood has zero range.

    The zone is a RANK zone -- the top and bottom `pct` of this image's own
    pixels -- so it is defined by order, not by value, and survives any
    strictly monotone tone map.  `flat` is an equality test, which survives the
    same maps for the same reason.

    Returns per-block counts so an interval can be bootstrapped over blocks;
    pixels within a block are not independent and treating them as such would
    understate the interval by orders of magnitude.
    """
    hi_t = np.percentile(g, 100.0 - pct)
    lo_t = np.percentile(g, pct)
    mx = ndimage.maximum_filter(g, 3)
    mn = ndimage.minimum_filter(g, 3)
    flat = (mx == mn)
    del mx, mn
    hi, lo = (g >= hi_t), (g <= lo_t)
    rows = []
    for (y, x) in (blocks if blocks is not None else _blocks(g.shape)):
        fb = flat[y:y + BLK, x:x + BLK]
        hb, lb = hi[y:y + BLK, x:x + BLK], lo[y:y + BLK, x:x + BLK]
        rows.append((int(hb.sum()), int((fb & hb).sum()),
                     int(lb.sum()), int((fb & lb).sum())))
    del flat, hi, lo
    a = np.array(rows, dtype=np.int64)
    return dict(rows=a,
                hi=float(a[:, 1].sum() / max(a[:, 0].sum(), 1)),
                lo=float(a[:, 3].sum() / max(a[:, 2].sum(), 1)),
                n_hi=int(a[:, 0].sum()), n_lo=int(a[:, 2].sum()),
                hi_t=float(hi_t), lo_t=float(lo_t))


def boot(rows, col_n, col_f, nboot=2000, seed=19):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(rows), size=(nboot, len(rows)))
    num = rows[:, col_f][idx].sum(axis=1)
    den = np.maximum(rows[:, col_n][idx].sum(axis=1), 1)
    r = num / den
    return float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def quantise(g, bits):
    n = float(2 ** bits - 1)
    return (np.round(np.clip(g, 0.0, 1.0) * n) / n).astype(np.float32)


def add_to(g, sigma, target, rng):
    """Raise `g` from its measured `sigma` to `target` in quadrature."""
    add = float(np.sqrt(max(target * target - sigma * sigma, 0.0)))
    if add <= 0.0:
        return g, 0.0
    return (g + rng.normal(0, add, g.shape)).astype(np.float32), add


def make_prep(sigma, target, seed):
    """The measurement regime as a single deterministic function.

    DETERMINISTIC ON PURPOSE.  The noise draw is reseeded on every call, so
    `prep(x)` is a pure function of `x`.  A fresh draw per call would make the
    byte-identical-clone null fail for a reason that has nothing to do with
    the image, and a null that fails for a bookkeeping reason trains its
    reader to ignore it.
    """
    add = float(np.sqrt(max(target * target - sigma * sigma, 0.0)))

    def prep(x):
        if add > 0.0:
            x = (x + np.random.default_rng(seed).normal(
                0, add, x.shape)).astype(np.float32)
        return quantise(x, 8)
    return prep


def show(tag, p, ci=None):
    s = (f"  {tag:<46} highlight {p['hi']*100:7.3f}%"
         f"{'' if not ci else f' [{ci[0][0]*100:6.3f},{ci[0][1]*100:6.3f}]'}"
         f"   shadow {p['lo']*100:7.3f}%"
         f"{'' if not ci else f' [{ci[1][0]*100:6.3f},{ci[1][1]*100:6.3f}]'}")
    print(s)
    d = dict(hi=p["hi"], lo=p["lo"], n_hi=p["n_hi"], n_lo=p["n_lo"])
    if ci:
        d["hi_ci"], d["lo_ci"] = list(ci[0]), list(ci[1])
    return d


def commission(g, sigma, ladder, rng, blocks, prep, regime):
    """Commission the gauge IN THE REGIME THE VERDICT IS COMPUTED IN.

    `prep` is the exact transform the measurement goes through.  The first
    version of this file ran every arm below at native bit depth and computed
    its verdict on 8-bit data, so its noise ladder reported 0.0000 pts for a
    confound worth 41 points.  Every arm here is therefore run as
    `plateau(prep(x))`, never `plateau(x)`.
    """
    out, ok = {}, True

    def rd(x):
        return plateau(prep(x), blocks=blocks)

    base = rd(g)
    print(f"  REGIME: {regime}")
    print(f"  {'THIS ARM, unmodified':<46} highlight {base['hi']*100:7.3f}%"
          f"   shadow {base['lo']*100:7.3f}%")
    print(f"     zone sizes: {base['n_hi']} highlight px, {base['n_lo']} "
          f"shadow px  (asked {ZONE_PCT}% each; ties at the threshold can")
    print(f"     inflate the realised zone, so it is printed, not assumed)")
    out["base"] = show("(recorded)", base)

    print("\n  -- NULL: a byte-identical clone")
    c = rd(g.copy())
    same = (c["hi"] == base["hi"] and c["lo"] == base["lo"])
    print(f"     identical: {same}")
    ok &= bool(same)

    print("\n  -- TONE INVARIANCE: three strictly monotone maps, applied to")
    print("     the STORED image -- i.e. after `prep`, which is what a viewer")
    print("     or a grader actually operates on.  A monotone map on an")
    print("     already-tied array preserves both order and equality, so the")
    print("     rank zone and the equality test are EXACTLY unchanged.")
    print("     Applying them BEFORE `prep` instead makes this test vacuous:")
    print("     at native 16-bit float the statistic is identically 0.000%,")
    print("     so `exact: True` would compare 0.000 with 0.000 and the")
    print("     solarise power test would report `moved: False` for a gauge")
    print("     that works.  That is the same regime error as the noise")
    print("     ladder, in a third place.")
    tone, stored = {}, prep(g)
    ref = plateau(stored, blocks=blocks)
    for nm, f in (("gamma 0.45", lambda a: np.clip(a, 0, 1) ** 0.45),
                  ("gamma 2.20", lambda a: np.clip(a, 0, 1) ** 2.20),
                  ("S-curve 3x^2-2x^3",
                   lambda a: (lambda b: (3 * b * b - 2 * b * b * b))(
                       np.clip(a, 0, 1)))):
        p = plateau(f(stored).astype(np.float32), blocks=blocks)
        exact = (p["hi"] == ref["hi"] and p["lo"] == ref["lo"])
        tone[nm] = dict(hi=p["hi"], lo=p["lo"], exact=bool(exact))
        print(f"     {nm:<20} highlight {p['hi']*100:7.3f}%  shadow "
              f"{p['lo']*100:7.3f}%   exact: {exact}")
        ok &= bool(exact)
    out["tone"] = tone

    print("\n  -- POWER OF THAT INVARIANCE: a NON-monotone map MUST move it.")
    print("     Without this line, a statistic that never moves at all would")
    print("     pass the invariance test perfectly by being blind.")
    sol = np.where(stored < np.median(stored), stored,
                   2.0 * np.median(stored) - stored).astype(np.float32)
    p = plateau(sol, blocks=blocks)
    moved = (p["hi"] != ref["hi"] or p["lo"] != ref["lo"])
    print(f"     solarise            highlight {p['hi']*100:7.3f}%  shadow "
          f"{p['lo']*100:7.3f}%   moved: {moved}")
    out["nonmonotone"] = dict(hi=p["hi"], lo=p["lo"], moved=bool(moved))
    ok &= bool(moved)
    del sol, stored, ref

    print("\n  -- DEGRADE: hard-clip the top and bottom 2%.  Must RISE.")
    hi_t, lo_t = np.percentile(g, 98.0), np.percentile(g, 2.0)
    d = np.clip(g, lo_t, hi_t).astype(np.float32)
    p = rd(d)
    rose = (p["hi"] > base["hi"] and p["lo"] > base["lo"])
    print(f"     hard-clipped        highlight {p['hi']*100:7.3f}%  shadow "
          f"{p['lo']*100:7.3f}%   rose: {rose}")
    out["degrade"] = dict(hi=p["hi"], lo=p["lo"], rose=bool(rose))
    ok &= bool(rose)

    print("\n  -- IMPROVE: a RESTORATION LADDER.  Detail destroyed by the")
    print("     clip is put back in a growing random fraction of BLOCKS, and")
    print("     the reading must fall monotonically.  Two earlier forms of")
    print("     this arm were wrong and are not used:")
    print("       * `0.5*clipped + 0.5*original` is strictly monotone in the")
    print("         original, so at infinite precision a rank-invariant")
    print("         statistic is OBLIGED to return to base -- it passes by")
    print("         construction and demonstrates nothing.  Worse, in THIS")
    print("         regime it halves the slope, so 8-bit quantisation ties")
    print("         MORE pixels than the restoration frees, and it read")
    print("         6.373% against a clipped 5.7% -- a restoration scoring")
    print("         as a degradation.")
    print("       * a single 50% restoration can move the rank threshold")
    print("         itself, so `between clipped and base` is not guaranteed")
    print("         even when the gauge is behaving.")
    print("     A ladder is robust to both: it is a TREND over five points,")
    print("     and it restores ORIGINAL amplitudes, never averaged ones.")
    lad_rows, prev, mono = [], None, True
    order = rng.permutation(len(blocks))
    for f in (0.0, 0.25, 0.5, 0.75, 1.0):
        m = np.zeros(g.shape, bool)
        for j in order[:int(round(f * len(blocks)))]:
            yy, xx = blocks[j]
            m[yy:yy + BLK, xx:xx + BLK] = True
        pf = rd(np.where(m, g, d).astype(np.float32))
        lad_rows.append((f, pf["hi"], pf["lo"]))
        print(f"     restored {f*100:5.1f}% of blocks   highlight "
              f"{pf['hi']*100:7.3f}%  shadow {pf['lo']*100:7.3f}%")
        del m
    strict = (lad_rows[-1][1] < lad_rows[0][1]
              and lad_rows[-1][2] < lad_rows[0][2])
    tol_hi = 0.05 * abs(lad_rows[0][1] - lad_rows[-1][1])
    tol_lo = 0.05 * abs(lad_rows[0][2] - lad_rows[-1][2])
    for a, b in zip(lad_rows, lad_rows[1:]):
        mono &= (b[1] <= a[1] + tol_hi and b[2] <= a[2] + tol_lo)
    print(f"     monotonically non-increasing within 5% of the total fall "
          f"({tol_hi*100:.3f}/{tol_lo*100:.3f} pts): {mono}")
    print(f"     fully-restored strictly below clipped: {strict}")
    print("     Both must hold.  Monotone alone would be satisfied by a flat")
    print("     line, which is what a gauge blind to restored detail returns;")
    print("     `strict` alone would be satisfied by a single lucky endpoint.")
    print("     The tolerance is scaled by the effect rather than absolute,")
    print("     because restoring blocks shifts the rank THRESHOLD slightly,")
    print("     so the zone is not identical between rungs.  A 0.03 pt wobble")
    print("     on a 7.7 pt fall is that shift, not a failure of response.")
    out["improve"] = dict(ladder=[[float(a), float(b), float(c)]
                                  for a, b, c in lad_rows],
                          monotone=bool(mono), strict=bool(strict),
                          tol=[float(tol_hi), float(tol_lo)])
    ok &= bool(mono and strict)
    del d

    print("\n  -- QUANTISATION LADDER: what the CONTAINER alone is worth.")
    print("     focus-stack writes 8-bit.  If the container moves this gauge")
    print("     further than the arms differ, then an unmatched comparison")
    print("     measures the container.")
    q = {}
    for b in (16, 14, 12, 10, 8):
        p = plateau(quantise(g, b), blocks=blocks)
        q[b] = dict(hi=p["hi"], lo=p["lo"])
        print(f"     {b:>2}-bit             highlight {p['hi']*100:7.3f}%"
              f"  shadow {p['lo']*100:7.3f}%")
    out["quant"] = q

    print("\n  -- NOISE LADDER, RUN THROUGH `prep`: the fooling direction.")
    print("     Noise breaks ties, so a noisier arm scores BETTER here for no")
    print("     merit.  V-NOISE2 measured the comparators noisier, so this")
    print("     bias runs against this project.  The previous version ran")
    print("     this ladder at native depth, where it could not move at all.")
    nz = {}
    for tag, target in ladder:
        x, add = add_to(g, sigma, target, rng)
        p = rd(x)
        nz[tag] = dict(hi=p["hi"], lo=p["lo"], added=float(add))
        mult = target / sigma if sigma else 1.0
        print(f"     to {tag:<12} ({mult:.2f}x, +{add:.6f})  highlight "
              f"{p['hi']*100:7.3f}%  shadow {p['lo']*100:7.3f}%")
        del x
    out["noise"] = nz
    return out, ok, base


def hp_std(a):
    return float((a - ndimage.uniform_filter(a, 9))[8:-8, 8:-8].std())


def run(key, rng):
    print("=" * 108)
    print(f"SUBJECT {key} = {ffarms.SUBJECTS[key]['name']}   "
          f"CLIPPING / EXTREME-ZONE DETAIL, free field")
    print(f"ZONE: top and bottom {ZONE_PCT}% by each arm's OWN rank; "
          f"statistic = 3x3 zero-range fraction")
    print("=" * 108)

    arms = ffarms.build(key)
    grid = ffarms.detail_grid(arms["strehl"].g, T=BLK)
    sig = {}
    for k in ffarms.KEYS:
        a = arms[k]
        t = a.tsize(BLK)
        rois = a.rois_for(grid, BLK)
        v = np.array([hp_std(a.g[y:y + t, x:x + t]) for (y, x) in rois])
        kk = max(int(len(rois) * 0.25), 8)
        sig[k] = float(np.median(v[np.argsort(v)[:kk]]))
        print(f"  {k:<10} {a.w}x{a.h} {a.bits}-bit   flat-tile sigma "
              f"{sig[k]:.6f}   ({a.label})")

    print("\n  THE CONTAINER CEILING, measured (this is the null result):")
    ceil = {}
    for k in ffarms.KEYS:
        a = arms[k]
        f = float((a.g >= 0.999999).mean())
        z = float((a.g <= 1e-6).mean())
        ceil[k] = dict(at_ceiling=f, at_floor=z)
        print(f"  {k:<10} at ceiling {f*100:.5f}%   at floor {z*100:.5f}%")
    print("  No arm clips.  The README's 32% is the PREDECESSOR's Lightroom")
    print("  pipeline and does not transfer to the free field.")

    noisiest = max(sig, key=lambda k: sig[k])
    target = sig[noisiest]
    print(f"\n{'='*108}")
    print("THE MEASUREMENT REGIME, fixed before anything is compared")
    print("=" * 108)
    print("  At NATIVE 16-bit float this statistic is identically 0.000% on")
    print("  every arm: nothing is ever exactly equal, so the gauge has no")
    print("  power there and no comparison is possible.  It only has power")
    print("  once a container ties pixels.  So the regime is:")
    print(f"     1. NOISE-MATCH every arm to the noisiest ({noisiest}, sigma")
    print(f"        {target:.6f}) by adding in quadrature, then")
    print("     2. CONTAINER-MATCH by requantising all arms to 8 bits.")
    print("  Both confounds are then common to all arms and what remains is")
    print("  the merge.  Noise matching is NOT cosmetic here: the unmatched")
    print("  8-bit comparison charged strehl 41 points for being the")
    print("  quietest arm.  Noise can only be ADDED, never removed, so every")
    print("  arm is raised to the noisiest -- which is the direction that")
    print("  discards this project's own measured noise advantage.")
    for k in ffarms.KEYS:
        add = float(np.sqrt(max(target ** 2 - sig[k] ** 2, 0.0)))
        print(f"     {k:<10} sigma {sig[k]:.6f} -> {target:.6f}   "
              f"adds {add:.6f}")

    preps = {k: make_prep(sig[k], target, 100 + i)
             for i, k in enumerate(ffarms.KEYS)}
    ladder = [("1.25x matched", 1.25 * target),
              ("1.50x matched", 1.50 * target),
              ("2.00x matched", 2.00 * target)]

    print(f"\n{'='*108}")
    print("COMMISSIONING, per arm, IN THAT REGIME")
    print("=" * 108)
    comm, base = {}, {}
    for k in ffarms.KEYS:
        a = arms[k]
        blocks = _blocks(a.g.shape)
        print(f"\n{'-'*108}\nARM {k}   {len(blocks)} blocks of {BLK} px")
        comm[k], ok, base[k] = commission(
            a.g, target, ladder, rng, blocks, preps[k],
            f"noise-matched to {target:.6f} then 8-bit")
        comm[k]["passed"] = bool(ok)
        print(f"\n  ARM {k} COMMISSIONING: {'PASS' if ok else 'FAIL'}")

    print(f"\n{'='*108}")
    print("THE MEASUREMENT -- NATIVE CONTAINERS, for the record only")
    print("  16-bit arms read exactly 0.000%: the null that says nobody")
    print("  clips.  fs15's 8-bit reading is its CONTAINER, not its merge,")
    print("  and is not comparable with the other two.")
    print("=" * 108)
    native = {}
    for k in ffarms.KEYS:
        p = plateau(arms[k].g, blocks=_blocks(arms[k].g.shape))
        ci = (boot(p["rows"], 0, 1), boot(p["rows"], 2, 3))
        native[k] = show(f"{k}  ({arms[k].bits}-bit, native)", p, ci)

    print(f"\n{'='*108}")
    print("THE MEASUREMENT -- NOISE-MATCHED AND CONTAINER-MATCHED")
    print("  The only admissible comparison on this gauge.")
    print("=" * 108)
    matched = {}
    for k in ffarms.KEYS:
        p = base[k]
        ci = (boot(p["rows"], 0, 1), boot(p["rows"], 2, 3))
        matched[k] = show(f"{k}  matched", p, ci)

    print("\n  VERDICT, comparator minus strehl, both confounds matched.")
    print("  Lower is better: a flat 3x3 neighbourhood in an extreme zone is")
    print("  detail that is gone.  The bar is what a 25% residual noise")
    print("  mismatch is worth on THIS arm in THIS regime -- measured, not")
    print("  assumed, because an unmatched mismatch was worth 41 points.")
    verdict = {}
    for k in ffarms.KEYS:
        if k == "strehl":
            continue
        rec = {}
        for ax in ("hi", "lo"):
            d = matched[k][ax] - matched["strehl"][ax]
            sl = comm["strehl"]["noise"].get("1.25x matched")
            lad = 0.0 if sl is None else abs(sl[ax] - base["strehl"][ax])
            sep = (matched[k][f"{ax}_ci"][0] > matched["strehl"][f"{ax}_ci"][1]
                   or matched[k][f"{ax}_ci"][1]
                   < matched["strehl"][f"{ax}_ci"][0])
            res = bool(sep and abs(d) > lad)
            who = "comparator worse" if d > 0 else "STREHL WORSE"
            print(f"  {k:<12} {'highlight' if ax == 'hi' else 'shadow':<10} "
                  f"{d*100:+8.4f} pts   noise bar {lad*100:.4f} pts   "
                  f"CIs disjoint {sep}  => "
                  f"{'RESOLVED, ' + who if res else 'UNRESOLVED'}")
            rec[ax] = dict(diff=float(d), ladder=float(lad), disjoint=bool(sep),
                           resolved=res, strehl_worse=bool(res and d < 0))
        verdict[k] = rec

    all_pass = all(comm[k]["passed"] for k in ffarms.KEYS)
    print(f"\n  ALL ARMS COMMISSIONED: {all_pass}")
    if not all_pass:
        print("  The tables above are NOT a result while an arm is "
              "uncommissioned.")

    for k in base:
        base[k].pop("rows", None)
    payload = dict(key=key, subject=ffarms.SUBJECTS[key], zone_pct=ZONE_PCT,
                   sigma_flat=sig, sigma_target=float(target),
                   noisiest=noisiest, ceiling=ceil, native=native,
                   matched=matched, verdict=verdict,
                   commissioning={k: {kk: vv for kk, vv in comm[k].items()}
                                  for k in comm},
                   all_pass=bool(all_pass),
                   bits={k: arms[k].bits for k in ffarms.KEYS})
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"clip-{key}.json"), "w",
              encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=float)
    print(f"\n  wrote {os.path.join(OUT, f'clip-{key}.json')}")
    return payload


def main(argv):
    keys = [a for a in argv if a in ffarms.SUBJECTS] or ["113", "119"]
    rng = np.random.default_rng(41)
    for k in keys:
        run(k, rng)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
