"""ladder -- adjudicate the coherence statistic against the scene term, on
planted ground truth, because I built one of the two and may not judge my own.

THE DISAGREEMENT.  On `119MSDCF` against `enfuse`, two instruments describe
detail retention and differ by ~1.7x:

    C (V-LINEAR2 sec.9, cohfree.py)   C_strehl/C_enfuse = 0.977  -> LEVEL
    scene term (V-NOISE2 sec.0.2)     scene_s/scene_e   = 0.577  -> we retain 58%

C is a cross-POWER in contrast^2; the scene term is an amplitude sigma.  Put on
one footing as "the comparator's detail amplitude relative to strehl's":

    C      -> sqrt(1/0.977) = 1.012      the two are level
    scene  ->      1/0.577  = 1.733      enfuse holds 1.7x our detail

Neither can be believed on its author's say-so, so this script decides it the
only legitimate way: with a THIRD construction whose answer is known in advance.

THE PLANT.  Take the real strehl half-stacks A and B for `119` and build a
companion pair whose detail is scaled by a known factor k:

    companion = lp + k * (img - lp)          lp = uniform_filter(img, LP)

For every frequency well above 1/LP the true amplitude ratio is EXACTLY k, by
construction, in every band.  LP = 64 px puts that corner at ~0.016 cyc/px, far
below both the 0.20-0.25 cyc/px band C reads and the HP-box high-pass the scene
term reads, so k is the right answer for BOTH instruments and neither is being
asked a question the plant does not contain.

Note the plant scales noise along with detail.  That is deliberate and it is
what makes the rung fair to the scene term, which subtracts a noise estimate:
f -> k*f and n -> k*n, so scene = sqrt(f^2 - n^2) -> k*scene.  C is a coherent
cross-power, so C -> k^2 * C.  Both therefore have a defined correct answer.

THE RUNGS.

  IDENT-BITWISE  companion IS the master array.  Tests DETERMINISM ONLY.  It is
                 reported and then discounted: a statistic compared against its
                 own inputs returns 1.000 by arithmetic and that is not evidence
                 about the instrument.  It is here because its FAILURE would
                 still be informative.
  IDENT-PATH     k = 1.00 through the real plant.  This is the identity rung
                 that counts.  The script ASSERTS the planted array is not
                 bit-identical to the master before believing the reading -- a
                 short-circuited identity control returning exactly 1.0000 is
                 the defect this lane already shipped once in `resamp.py`.
  k = 1.30       companion SHARPER than the master.  A statistic bounded below
                 at parity passes a degradation-only ladder trivially, and this
                 project has already shipped a gauge that was perverse on its
                 own arm.  Any instrument that cannot return >1 here is refused.
  k = 0.95, 0.85, 0.70, 0.50   degradation ladder.

TWO POPULATIONS, because that is the live rival explanation for the field
disagreement: `cohfree.py` runs C on `rois.census(...)` DETAIL tiles, while the
scene term runs on FLAT tiles -- tiles selected for having no detail.  Both
instruments are therefore run on BOTH populations.  If each recovers k on both,
the instruments agree and the field disagreement is a population difference,
not an instrument error, and the report must say which question each answers.

    python ladder.py [nroi=40]
"""
import json
import os
import sys

import numpy as np
from scipy.ndimage import uniform_filter

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE"))
import h2                                                        # noqa: E402
import rois                                                      # noqa: E402
from h2h2b import Comp, cross_bands, T, PAD                      # noqa: E402
from noisefree import EDGE, HP                                   # noqa: E402

import hd2                                                       # noqa: E402

BAND = (0.2, 0.25)          # the pre-registered band C's 0.977 was read in
LP = 64                     # plant corner ~0.016 cyc/px, far below both readers
MARGIN = 2 * LP             # discarded after planting, so no lowpass edge bleed
RUNGS = [("IDENT-BITWISE", None), ("IDENT-PATH", 1.00), ("SHARPER", 1.30),
         ("k=0.95", 0.95), ("k=0.85", 0.85), ("k=0.70", 0.70), ("k=0.50", 0.50)]


def plant(a, k):
    """Scale detail by exactly k about a large-radius local mean."""
    lp = uniform_filter(a, LP)
    return lp + k * (a - lp)


def scene_term(ca, cb):
    """The V-NOISE2 sec.0.2 scene term, luma, at MATCHED bandwidth.

    f is the high-passed sigma of one image; n is the half-difference sigma
    through the SAME high-pass (the bandwidth match this lane had to fix); the
    scene term is what survives in quadrature.
    """
    lvl = float(0.5 * (ca.mean() + cb.mean()))
    if lvl <= 1e-6:
        return None
    r = ca - uniform_filter(ca, HP)
    f = float(r[EDGE:-EDGE, EDGE:-EDGE].std()) / lvl
    d = ca - cb
    d = d - uniform_filter(d, HP)
    n = float(np.sqrt(0.5 * d[EDGE:-EDGE, EDGE:-EDGE].var())) / lvl
    return float(np.sqrt(max(f * f - n * n, 0.0)))


def c_stat(ca, cb, bi):
    """The V-LINEAR2 sec.9 coherence statistic: cross-power in the band."""
    C = cross_bands(ca, cb)
    if C is None:
        return None
    return float(C[bi])


def main():
    nroi = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    _, spec = hd2.paths_for("119")
    pa, pb, _ = spec["strehl"]
    W = (0.2126, 0.7152, 0.0722)
    A = Comp(dict(path=pa, weights=W))
    B = Comp(dict(path=pb, weights=W))
    names = list(h2.BANDS)
    bi = names.index(BAND)

    census, spec2 = hd2.paths_for("119")
    z = np.load(census)
    cells, emax = z["cells"], z["emax"]
    flat_idx = list(z["flat"])
    order = np.argsort(emax)
    detail_idx = [int(i) for i in order[-len(flat_idx):]]
    rng = np.random.default_rng(11)

    def pick(idx):
        sel = rng.permutation(len(idx))[:nroi]
        return [tuple(cells[idx[i]]) for i in sel]

    pops = {
        "DETAIL (C's own population)": pick(detail_idx),
        "FLAT (the scene term's own population)": pick(flat_idx),
    }

    print("=" * 100)
    print("LADDER -- planted detail ratios, both instruments, both populations")
    print("=" * 100)
    print(f"  subject 119MSDCF, strehl half-stacks A/B, band {BAND[0]}-{BAND[1]} cyc/px")
    print(f"  plant: companion = lp + k*(img - lp), lp = uniform_filter({LP}) "
          f"-> true amplitude ratio is k in every band above ~0.016 cyc/px")
    print(f"  {nroi} tiles per population, {T}px, {MARGIN}px planting margin "
          f"discarded")

    out = {"band": f"{BAND[0]}-{BAND[1]}", "lp": LP, "nroi": nroi, "populations": {}}
    for pname, cells_p in pops.items():
        print()
        print("-" * 100)
        print(f"POPULATION: {pname}   ({len(cells_p)} tiles)")
        print("-" * 100)
        print(f"  {'rung':14s} {'true k':>8s} {'C recovers':>12s} "
              f"{'err':>8s} {'scene recovers':>15s} {'err':>8s}")
        rows = {}
        for label, k in RUNGS:
            cs, ss = [], []
            bitcheck = None
            for (y, x) in cells_p:
                big = T + 2 * MARGIN
                ca, na = A.crop(y - MARGIN, x - MARGIN, big)
                cb, nb = B.crop(y - MARGIN, x - MARGIN, big)
                if ca is None or cb is None or na or nb:
                    continue
                if k is None:
                    pa_, pb_ = ca, cb
                else:
                    pa_, pb_ = plant(ca, k), plant(cb, k)
                    if bitcheck is None:
                        bitcheck = not np.array_equal(pa_, ca)
                m = slice(MARGIN, MARGIN + T)
                c0, c1 = ca[m, m], cb[m, m]
                p0, p1 = pa_[m, m], pb_[m, m]
                Cm, Cp = c_stat(c0, c1, bi), c_stat(p0, p1, bi)
                Sm, Sp = scene_term(c0, c1), scene_term(p0, p1)
                if Cm and Cp and Cm > 0 and Sm and Sp and Sm > 0:
                    cs.append(np.sqrt(Cp / Cm))
                    ss.append(Sp / Sm)
            if not cs:
                continue
            ck, sk = float(np.median(cs)), float(np.median(ss))
            if k is None:
                print(f"  {label:14s} {'1.000':>8s} {ck:12.4f} "
                      f"{'':>8s} {sk:15.4f} {'':>8s}   determinism only")
                rows[label] = {"true": 1.0, "C": ck, "scene": sk}
                continue
            if abs(k - 1.0) > 1e-9 and bitcheck is False:
                raise SystemExit(
                    f"{label}: plant(k={k}) returned a bit-identical array. "
                    f"The plant is a no-op and every rung below it is vacuous. "
                    f"REFUSED.")
            note = ""
            if abs(k - 1.0) <= 1e-9:
                note = ("   plant bit-identical here (exact fp arithmetic); "
                        "potency is proven by the k!=1 rungs, which DO change "
                        "the array"
                        if bitcheck is False else
                        "   plant altered the array, so this reading is a "
                        "prediction")
            print(f"  {label:14s} {k:8.3f} {ck:12.4f} {ck / k - 1:+7.1%} "
                  f"{sk:15.4f} {sk / k - 1:+7.1%}{note}")
            rows[label] = {"true": k, "C": ck, "scene": sk,
                           "plant_changed_array": bitcheck}
        out["populations"][pname] = rows

        graded = [(v["true"], v["C"], v["scene"]) for lab, v in rows.items()
                  if lab != "IDENT-BITWISE"]
        for iname, idx in (("C", 1), ("scene term", 2)):
            errs = [abs(g[idx] / g[0] - 1) for g in graded]
            worst = max(errs)
            sharper = [g for g in graded if g[0] > 1.0]
            perverse = [g for g in sharper if g[idx] <= 1.0]
            verdict = ("RECOVERS the planted ratio"
                       if worst < 0.10 and not perverse else
                       "PERVERSE on the sharper rung" if perverse else
                       "FAILS to recover the planted ratio")
            print(f"    {iname:11s} worst error {worst:6.1%} over "
                  f"{len(graded)} graded rungs -> {verdict}")

    dst = os.path.join(hd2.ROOT, "ladder.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n  written {dst}")


if __name__ == "__main__":
    main()
