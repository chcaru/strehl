r"""Acceptance instrument for a mid-scale-mottle fix.

WHAT IT MEASURES, and why each term is here
-------------------------------------------
The convicting gauge is V-GATHER / ORCH-drift-check `orch_blotch.blotch_ratio`:
band-pass 50-400 px in the flattest region, expressed as `band/mean` so it is
invariant to a linear gain. It is IMPORTED, not reimplemented, so that a fix is
scored on the same statistic that convicted the subject.

Three terms are carried on THE SAME PIXELS, and the third is the whole point:

  blotch    = std(band 50-400 px) / mean      LOW IS GOOD
  noise     = std(blk - blur3)    / mean      must NOT fall with blotch
  sharp     = mean|grad|          / mean      must NOT fall

A fix that smooths mottle by smoothing the image lowers ALL THREE. A real fix
lowers only the first. Without `noise` and `sharp` on the same pixels, a
Gaussian blur is indistinguishable from a merge repair -- and a blur is exactly
what a careless fix produces.

THE COMMISSIONING SUITE PLANTS AN IMPROVEMENT, NOT ONLY A DEFECT.
This project shipped a sharpness statistic whose error sign was bounded below by
zero -- it could ignore a halo but never charge for one -- because every arm ever
planted was a degradation. A defect-only suite cannot tell a BLIND gauge from a
PERVERSE one. Arms here:

  clone           identical copy            -> nothing moves             (null)
  gain x1.5       linear scaling            -> nothing moves             (invariance)
  mottle+         planted mid-scale blobs   -> blotch UP                 (defect)
  mottle+ repair  75% of that plant removed -> blotch DOWN vs the defect (IMPROVEMENT)
  band- global    band removed EVERYWHERE   -> blotch DOWN, detail LOST  (CHEAT: must be flagged)
  blur s2         Gaussian sigma 2          -> sharp DOWN                (fine-scale CHEAT)

The improvement arm is a LADDER WITH KNOWN GROUND TRUTH: the suite degrades the
image by an amount it chose, then removes three quarters of exactly that
degradation. A gauge that is BLIND to the defect cannot show the ladder; a gauge
that is PERVERSE on it shows the ladder running backwards. Only a gauge that
responds correctly in BOTH directions produces a monotone ladder -- and the
repair must be credited WITHOUT moving `sharp` or `blotch(detail)`, which is
what separates a repair from a softening.

`band- global` deletes precisely the quantity being reported, everywhere, and so
scores a PERFECT headline number on the flat tiles. It is convicted only on
`blotch(detail)`. The first version of this suite used a sigma-2 Gaussian as its
cheat; measurement showed sigma 2 px moves the 50-400 px band by 0.7%, so that
arm never threatened the headline number and the suite was rebuilt around a
cheat that can actually reach it.

WINDOWS ARE PINNED ON THE REFERENCE ARM AND REUSED.
Letting each arm choose its own flattest window compares different pieces of the
subject and calls the difference a fix. All arms here come from ONE binary with
ONE alignment, so they are pixel-aligned by construction and no inter-arm
registration is needed or performed.
"""
import os
import sys

import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "ORCH-drift-check")))
from orch_blotch import boxblur, lum_of, LO_R, HI_R, NOISE_R  # noqa: E402

TILE = 900
N_TILES = 12
BOOT = 2000


def tile_grid(shape, tile=TILE):
    h, w = shape
    ys = list(range(0, h - tile + 1, tile))
    xs = list(range(0, w - tile + 1, tile))
    return [(y, x) for y in ys for x in xs]


def texture(lum, y, x, tile=TILE):
    d = lum[y:y + tile:8, x:x + tile:8]
    return float(np.mean(np.abs(np.diff(d, axis=0)[:, :-1]) + np.abs(np.diff(d, axis=1)[:-1, :])))


def pick_tiles(lum, n=N_TILES, tile=TILE):
    """The n flattest non-overlapping tiles. Blotch is only legible where the subject is not."""
    cand = tile_grid(lum.shape, tile)
    scored = sorted(cand, key=lambda p: texture(lum, p[0], p[1], tile))
    return scored[:n]


def pick_detail_tiles(lum, n=N_TILES, tile=TILE):
    """The n MOST textured tiles.

    These are the guard against a fix that is really a mid-scale blur. A blur at
    the blotch scale looks identical to a repair on flat tiles; it is only
    distinguishable where the subject genuinely carries 50-400 px structure.
    """
    cand = tile_grid(lum.shape, tile)
    scored = sorted(cand, key=lambda p: -texture(lum, p[0], p[1], tile))
    return scored[:n]


def terms(blk):
    """(blotch, noise, sharp), all divided by the block mean so a linear gain cancels."""
    m = float(np.mean(blk))
    if m <= 0:
        return float("nan"), float("nan"), float("nan")
    band = boxblur(blk, LO_R // 2) - boxblur(blk, HI_R // 2)
    noise = blk - boxblur(blk, NOISE_R)
    gy = np.abs(np.diff(blk, axis=0))[:, :-1]
    gx = np.abs(np.diff(blk, axis=1))[:-1, :]
    return (float(np.std(band)) / m,
            float(np.std(noise)) / m,
            float(np.mean(gy + gx)) / m)


def measure(lum, tiles):
    """Per-tile terms at PINNED coordinates. Returns arrays (n_tiles, 3)."""
    return np.array([terms(lum[y:y + TILE, x:x + TILE]) for (y, x) in tiles], dtype=np.float64)


def boot_ratio(a, b, rng, boot=BOOT):
    """Median ratio b/a over paired tiles, with a percentile CI.

    Paired: every tile is the SAME pixels in both arms, so the pairing is real
    and removes between-tile variation, which dominates.
    """
    r = b / a
    idx = rng.integers(0, len(r), size=(boot, len(r)))
    d = np.median(r[idx], axis=1)
    return float(np.median(r)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


# ---------------------------------------------------------------- commissioning

def _blobs(shape, rng, amp=1.0):
    """Mid-scale blob field, planted in EXACTLY the band the gauge measures.

    The first version used boxblur radii 90/360 while `terms` measures 25/200.
    Most of the planted energy therefore landed outside the measured band, and
    a plant sized at 0.6x the base band moved the statistic by 7.6% instead of
    the 16.6% that sqrt(1 + 0.6^2) predicts -- and by only 3.1% on `foam`, which
    failed the gate. A plant must live in the band it is meant to test.
    """
    n = rng.standard_normal(shape).astype(np.float32)
    b = boxblur(n, LO_R // 2) - boxblur(n, HI_R // 2)
    return (amp * b / (np.std(b) + 1e-12)).astype(np.float32)


def commission(lum, flat_tiles, detail_tiles, rng, verbose=True):
    """Plant a defect, a GROUND-TRUTHED repair of that defect, and a cheat.

    THE IMPROVEMENT ARM IS A LADDER WITH KNOWN GROUND TRUTH.
    Three attempts to build a "selective fix" plant in image space all failed,
    and the third failed for a reason that is a fact about the corpus rather
    than a bug: a macro `detail` tile is 86% smooth bokeh with sparse structure,
    so a flatness mask cannot separate the tile classes and every such plant
    degenerates into the uniform cheat. The plant audit made that visible
    (coverage 0.999 flat against 0.864 detail) instead of leaving it to be
    inferred from a mysteriously failing verdict.

    So the improvement is defined against a defect this suite planted itself:

        base            lum                      ground truth
        mottle+         lum + b                  degraded by a KNOWN amount
        mottle+ repair  lum + 0.25*b             75% of that degradation removed

    A gauge that is BLIND to the defect cannot show the ladder. A gauge that is
    PERVERSE on it -- like the sharpness statistic this project shipped, whose
    error sign was bounded below by zero so it could ignore a halo but never
    charge for one -- shows the ladder running the wrong way. Only a gauge that
    responds correctly in BOTH directions produces a monotone ladder, and the
    repair is credited without touching `sharp` or `blotch(detail)`, which is
    what separates the credit from a softening.

    The cheat, `band- global`, deletes precisely the quantity being reported,
    everywhere. On the flat tiles it scores a PERFECT headline number. It is
    convicted on `blotch(detail)`, where the same subtraction strips genuine
    50-400 px content that the ladder's repair leaves untouched.

    `blur s2` is the fine-scale cheat, caught by `sharp`. It is retained but it
    is not the interesting one: measurement showed a sigma-2 Gaussian moves the
    50-400 px band by 0.7%, so it never threatened the headline number at all.
    """
    m = float(np.mean(lum))
    band = (boxblur(lum, LO_R // 2) - boxblur(lum, HI_R // 2)).astype(np.float32)

    # Size the planted defect in units of THE THING BEING MEASURED, not of the
    # image mean. The first version planted 0.010*mean and moved the statistic
    # 0.7%, because the subject's own band power is far larger than that.
    base_f = measure(lum, flat_tiles)
    base_band = float(np.median(base_f[:, 0])) * m
    b = _blobs(lum.shape, rng, amp=0.6 * base_band)

    arms = {
        "clone": lum.copy(),
        "gain x1.5": (lum * 1.5).astype(np.float32),
        "mottle+": (lum + b).astype(np.float32),
        "mottle+ repair": (lum + 0.25 * b).astype(np.float32),
        "band- global": (lum - 0.75 * band).astype(np.float32),
    }
    try:
        from scipy.ndimage import gaussian_filter
        arms["blur s2"] = gaussian_filter(lum, 2.0).astype(np.float32)
    except Exception:
        arms["blur s2"] = boxblur(lum, 2)

    F = {"base": base_f}
    D = {"base": measure(lum, detail_tiles)}
    for name, img in arms.items():
        F[name] = measure(img, flat_tiles)
        D[name] = measure(img, detail_tiles)

    def ratio(tab, num, den, i):
        return boot_ratio(tab[den][:, i], tab[num][:, i], rng)

    def rf(name, i, den="base"):
        return ratio(F, name, den, i)[0] - 1.0

    def rd(name, i, den="base"):
        return ratio(D, name, den, i)[0] - 1.0

    tol = 0.01
    v = {}
    # The ladder is checked for monotonicity FIRST: it is a statement about the
    # plant, and a plant that does not step cannot commission anything.
    v["LADDER is monotone"] = (rf("mottle+", 0) > rf("mottle+ repair", 0) > -0.02)
    v["clone unmoved"] = all(abs(rf("clone", i)) < 1e-9 for i in range(3))
    v["gain invariant"] = all(abs(rf("gain x1.5", i)) < tol for i in range(3))
    v["DEFECT raises blotch"] = rf("mottle+", 0) > 0.05
    v["IMPROVEMENT credited"] = rf("mottle+ repair", 0, "mottle+") < -0.05

    # THE REPAIR IS JUDGED AGAINST GROUND TRUTH, NOT AGAINST THE DEFECT.
    # An earlier gate required `sharp(repair) >= sharp(defect) - 5%` and failed
    # on three of four subjects, because the planted field is not spectrally
    # pure -- box filters have a poor stopband, so the plant carries fine-scale
    # energy and RAISES sharp by 21-30% on the cleaner subjects. Undoing that
    # inflation is the repair working, and the old gate convicted it for that.
    # Ground truth is known here exactly, so the correct statement is that every
    # term moves TOWARD base. That is also a stricter test: it must hold in all
    # four terms at once.
    toward = []
    for tab, i, nm in ((F, 0, "blotch(flat)"), (F, 1, "noise(flat)"),
                       (F, 2, "sharp(flat)"), (D, 0, "blotch(detail)")):
        dd = abs(ratio(tab, "mottle+", "base", i)[0] - 1.0)
        rr = abs(ratio(tab, "mottle+ repair", "base", i)[0] - 1.0)
        toward.append((nm, dd, rr, rr <= dd + 0.002))
    v["repair moves ALL terms to truth"] = all(t[3] for t in toward)

    v["cheat lowers blotch"] = rf("band- global", 0) < -0.05
    v["CHEAT convicted on detail"] = rd("band- global", 0) < -0.10
    v["fine blur caught by sharp"] = rf("blur s2", 2) < -0.10

    if verbose:
        print("  COMMISSIONING (ratio to base; 1.000 = unmoved)")
        print("    %-15s %-21s %-21s %-21s %s"
              % ("arm", "blotch(flat)", "noise(flat)", "sharp(flat)", "blotch(detail)"))
        for name in arms:
            c = ["%.4f [%.4f,%.4f]" % ratio(F, name, "base", i) for i in range(3)]
            d0 = "%.4f [%.4f,%.4f]" % ratio(D, name, "base", 0)
            print("    %-15s %-21s %-21s %-21s %s" % (name, c[0], c[1], c[2], d0))
        print("    ladder, repair measured against the DEFECT it repairs:")
        print("    %-15s %-21s %-21s %-21s %s"
              % ("  repair/defect",
                 "%.4f [%.4f,%.4f]" % ratio(F, "mottle+ repair", "mottle+", 0),
                 "%.4f [%.4f,%.4f]" % ratio(F, "mottle+ repair", "mottle+", 1),
                 "%.4f [%.4f,%.4f]" % ratio(F, "mottle+ repair", "mottle+", 2),
                 "%.4f [%.4f,%.4f]" % ratio(D, "mottle+ repair", "mottle+", 0)))
        print("    distance from ground truth, |ratio-1|, defect -> repair:")
        print("      " + "   ".join("%s %.4f->%.4f%s" % (n, d, r, "" if o else " <-- AWAY")
                                    for (n, d, r, o) in toward))
        print()
        for k, val in v.items():
            print("    %-28s %s" % (k, "PASS" if val else "FAIL"))
    return all(v.values()), v, (F, D)


def load_lum(path, expect=None):
    """Read and VERIFY THE LATTICE FROM THE FILE rather than trusting the flags."""
    with tifffile.TiffFile(path) as t:
        pg = t.pages[0]
        w, h = pg.tags["ImageWidth"].value, pg.tags["ImageLength"].value
        desc = str(pg.tags["ImageDescription"].value) if "ImageDescription" in pg.tags else ""
    if "Tone rendering" in desc:
        raise SystemExit("REFUSED: %s carries a fitted tone stage; not a linear gauge" % path)
    if expect is not None and (w, h) != expect:
        raise SystemExit("REFUSED: lattice %dx%d != reference %dx%d" % (w, h, expect[0], expect[1]))
    a = tifffile.imread(path)
    return lum_of(a[:, :, :3].astype(np.float32)), (w, h)
