"""
foam_retract.py -- re-decide the `foam` specular fringing against the mechanism
another lane published, by measuring it here rather than deferring to it.

WHY THIS EXISTS.  §8.5 of docs/research/V-HEADTOHEAD2.md concluded the fringing
is REAL scene colour ("subject, not defect").  README lines 517-540 report a
different verdict from a better instrument: a channel-asymmetric highlight
saturation in strehl's own output, where GREEN's ceiling sits below BLUE's, so
a brightening highlight pins green first and acquires a one-sided blue excess.

Those cannot both be right.  This lane does not settle that by reading the
other lane's prose -- the same discipline that was applied to V-LINEAR2's
band-signal correction applies here, and it applies harder because this time
the imported result overturns my own conclusion rather than flattering it.

WHAT KILLED §8.5'S REASONING, stated before the measurement so it cannot be
retrofitted.  §8.5's load-bearing arm was RETENTION THROUGH THE MERGE: foam
kept 70.9% of its photosite chroma across a 100-frame merge where polished
steel kept 15.9%, and I read that as "scene-locked colour survives averaging,
phase-random Bayer aliasing does not".  That inference has a hole.  It
separates DETERMINISTIC from PHASE-RANDOM.  It does not separate SCENE from
PIPELINE, because a deterministic pipeline defect keyed to signal LEVEL is
also frame-invariant, and level is set by the scene, so it tracks the scene
through the merge exactly as real colour would.  A channel-ceiling asymmetry
is precisely such a defect.  §8.5 measured the right quantity and drew the
wrong dichotomy from it.

THE THREE ARMS, each of which can independently refute the ceiling mechanism:

  A. CEILINGS.  If the mechanism is real, the rendered master's green channel
     must top out BELOW blue.  If green's ceiling >= blue's, the mechanism is
     dead and §8.5 may stand.
  B. LEVEL DEPENDENCE.  B/G must climb MONOTONICALLY with luminance.  This is
     the arm that discriminates against white balance: a fixed WB gain makes
     B/G a constant multiple INDEPENDENT of level, so a rising B/G cannot be
     WB and a flat B/G cannot be a ceiling.
  C. HUE SIGN.  Thin-film interference cycles hue through BOTH signs as film
     thickness varies -- that is what makes it iridescence rather than a tint.
     A one-sided B-G excess on hot edge pixels is therefore positive evidence
     AGAINST interference, not merely absence of evidence for it.

Arm C is the one §8.5 should have run and did not.  §8.5 noticed the related
fact (46.7% single-pixel colour components: speckle, not ordered fringes) and
under-weighted it.

COMMISSIONING.  Every arm is run against planted inputs whose true answer is
fixed by construction, in BOTH directions, because an arm that has only ever
been shown to fire on the accused is not evidence:
  - a synthetic IRIDESCENT rim (hue cycling both signs, no channel ceiling)
    must FAIL to reproduce the mechanism;
  - a synthetic CEILING defect (green clipped low, hue never cycling) must
    reproduce it;
  - a FLAT-GREY ramp with no colour at all must show no B/G trend, which
    catches an arm that reports a trend from level alone.

Reads .tiff with tifffile per this project's rule; PIL is never used here.
"""

import os
import sys

import numpy as np
import tifffile

SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"
MASTER = os.path.join(SHIP, "foam--SHIP-V4.tiff")

# The crop the owner was looking at when he raised this, from DELIVER-V5.
# x=3466, y=1698 per the `name_X_Y.png` convention.
CROP_X, CROP_Y, CROP_W = 3466, 1698, 380


def ceilings(rgb):
    """Arm A. Per-channel ceiling, as the level each channel actually tops out
    at. True max is fragile to a single hot pixel, so the 99.999 percentile is
    reported beside it and the verdict uses the max, which is what a ceiling
    physically is."""
    return [(int(rgb[..., c].max()), float(np.percentile(rgb[..., c], 99.999)))
            for c in range(3)]


def bg_by_decile(rgb, nbin=9):
    """Arm B. B/G against luminance decile.

    A fixed white-balance gain makes B/G a CONSTANT multiple independent of
    level; only a channel that saturates early can make it climb. Pixels where
    green is zero are dropped rather than clamped, so the ratio is never
    manufactured by a divide-by-epsilon."""
    g = rgb[..., 1].astype(np.float64)
    b = rgb[..., 2].astype(np.float64)
    lum = rgb.astype(np.float64).mean(axis=2)
    ok = g > 0
    g, b, lum = g[ok], b[ok], lum[ok]
    if lum.size < 1000:
        return []
    edges = np.percentile(lum, np.linspace(10, 100, nbin + 1))
    out = []
    for i in range(nbin):
        m = (lum >= edges[i]) & (lum < edges[i + 1]) if i < nbin - 1 \
            else (lum >= edges[i])
        if m.sum() >= 50:
            out.append(float(np.median(b[m] / g[m])))
    return out


def hue_sign(rgb, hot_pct=99.0):
    """Arm C. Fraction of HOT pixels carrying a POSITIVE B-G.

    Interference cycles hue through both signs, so a film should land near
    0.5. ANY strong departure from 0.5 refutes it -- a green-excess pin drives
    this toward 0.0 exactly as a blue-excess pin drives it toward 1.0.

    GATE REPAIRED AFTER THE REAL DATA EXPOSED IT.  The first version gated on
    `frac > 0.75`, which can only charge a BLUE excess.  The foam master reads
    0.313, i.e. 68.7% of hot pixels carry a GREEN excess -- one-sided, and the
    one-directional gate called it "mixed". A statistic that can only convict
    in the direction you expected is the defect this project keeps finding in
    its own instruments (a sharpness error bounded below by zero that could
    never charge for a halo). The gate is now two-sided on |frac - 0.5|."""
    lum = rgb.astype(np.float64).mean(axis=2)
    thr = np.percentile(lum, hot_pct)
    m = lum >= thr
    if m.sum() < 100:
        return float("nan"), 0
    d = rgb[..., 2].astype(np.float64)[m] - rgb[..., 1].astype(np.float64)[m]
    return float((d > 0).mean()), int(m.sum())


def one_sided(frac, tol=0.25):
    """Two-sided test: interference must sit near 0.5 in EITHER direction."""
    return bool(np.isfinite(frac) and abs(frac - 0.5) > tol)


def monotone_frac(seq):
    """Fraction of adjacent steps that rise. 1.0 is strictly monotone."""
    if len(seq) < 2:
        return float("nan")
    return float(np.mean([seq[i + 1] > seq[i] for i in range(len(seq) - 1)]))


# ---------------------------------------------------------------- commissioning

def _plant_iridescent(n=400, peak=60000):
    """A rim whose hue CYCLES through both signs -- real interference -- with
    NO channel ceiling. Arms A/B/C must all decline to convict."""
    rng = np.random.default_rng(11)
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(y - n / 2, x - n / 2)
    rim = np.exp(-((r - n / 3) ** 2) / (2 * 6.0 ** 2))
    base = 8000 + rim * (peak - 8000)
    # thickness-driven phase: B-G swings through BOTH signs around the rim
    th = np.arctan2(y - n / 2, x - n / 2)
    swing = 0.25 * np.sin(4 * th)
    img = np.zeros((n, n, 3))
    # PLANT REPAIRED.  The first version used R=base*(1-swing/2), which made
    # R+G+B depend on `swing`, so luminance correlated with hue sign and the
    # hot-pixel selection preferentially drew one sign: the arm then "passed"
    # on this plant for the wrong reason. Keeping the channel sum constant
    # makes luminance independent of hue, which is what a real film does.
    img[..., 0] = base
    img[..., 1] = base * (1 - swing)
    img[..., 2] = base * (1 + swing)
    img += rng.normal(0, 30, img.shape)
    return np.clip(img, 0, 65535).astype(np.uint16)


def _plant_ceiling(n=400, g_ceil=38921, b_ceil=52239):
    """A NEUTRAL grey field with no scene colour whatsoever, passed through a
    channel-asymmetric ceiling. Arms A/B/C must all convict.

    COMMISSIONING FORCED A REPAIR HERE.  The first version of this plant was a
    narrow Gaussian rim on a flat 8000 base, so ~80% of pixels sat at one level
    and eight of nine deciles were identical: the planted defect was real but
    invisible to a decile statistic.  A plant whose level distribution is
    degenerate cannot exercise a level-dependent arm.  Replaced with a
    continuous luminance ramp crossing the ceiling, which is what a real
    highlight roll-off looks like."""
    rng = np.random.default_rng(12)
    y, x = np.mgrid[0:n, 0:n]
    # continuous ramp spanning well below to well above the green ceiling
    base = 6000 + (x / n) * 59000 + (y / n) * 400
    img = np.repeat(base[..., None], 3, axis=2)
    img += rng.normal(0, 30, img.shape)
    img[..., 1] = np.minimum(img[..., 1], g_ceil)
    img[..., 2] = np.minimum(img[..., 2], b_ceil)
    return np.clip(img, 0, 65535).astype(np.uint16)


def _plant_flat(n=400):
    """A colourless luminance ramp. Arm B must report NO trend; if it does,
    the arm is reading level rather than channel behaviour."""
    rng = np.random.default_rng(13)
    y, x = np.mgrid[0:n, 0:n]
    base = 4000 + (x / n) * 50000
    img = np.repeat(base[..., None], 3, axis=2) + rng.normal(0, 30, (n, n, 3))
    return np.clip(img, 0, 65535).astype(np.uint16)


def commission():
    print("COMMISSIONING -- planted inputs, true answer fixed by construction\n")
    rows, ok = [], True

    for name, img, want_ceiling, want_trend, want_sign in (
            ("IRIDESCENT (real film, no ceiling)", _plant_iridescent(),
             False, False, False),
            ("CEILING (no colour, green pins low)", _plant_ceiling(),
             True, True, True),
            ("FLAT (no colour, no ceiling)", _plant_flat(),
             False, False, None),
    ):
        cl = ceilings(img)
        gc, bc = cl[1][0], cl[2][0]
        has_ceiling = gc < bc * 0.95
        seq = bg_by_decile(img)
        mono = monotone_frac(seq)
        # CRITERION REPAIRED BY COMMISSIONING.  The first version required
        # monotone >= 0.75 across all deciles.  That is stricter than the
        # physics: a channel ceiling produces a HOCKEY STICK -- B/G is flat
        # while green is below its ceiling and rises only once green pins --
        # so a defect confined to highlights, which is the ONLY place a
        # highlight defect can live, would have been acquitted.  The
        # discriminating fact against white balance is that a fixed WB gain
        # makes B/G a CONSTANT independent of level; therefore ANY reliable
        # rise refutes WB, monotone or hockey stick.  Rise is the test;
        # monotonicity is reported but is not the gate.
        trend = (len(seq) >= 2 and seq[-1] > seq[0] * 1.05)
        frac, _ = hue_sign(img)
        onesided = one_sided(frac)

        print(f"  {name}")
        print(f"    ceilings G={gc} B={bc}  -> green-pins-first={has_ceiling}"
              f" (want {want_ceiling})")
        print(f"    B/G deciles {' '.join('%.3f' % v for v in seq)}")
        print(f"    monotone={mono:.2f} -> rising-trend={trend}"
              f" (want {want_trend})")
        print(f"    hot B-G>0 frac={frac:.3f} -> one-sided={onesided}"
              + (f" (want {want_sign})" if want_sign is not None else ""))

        for label, got, want in (("ceiling", has_ceiling, want_ceiling),
                                 ("trend", trend, want_trend),
                                 ("sign", onesided, want_sign)):
            if want is None:
                continue
            good = (got == want)
            ok = ok and good
            rows.append((f"{name.split()[0]}-{label}", good))
        print()

    for n, g in rows:
        print(f"  [{'PASS' if g else 'FAIL'}] {n}")
    print(f"\n  {sum(1 for _, g in rows if g)} of {len(rows)} arms correct")
    return ok


def main():
    if "--commission" in sys.argv:
        sys.exit(0 if commission() else 1)

    if not os.path.exists(MASTER):
        print(f"MISSING: {MASTER}")
        sys.exit(2)

    mm = tifffile.memmap(MASTER, mode="r")
    print(f"master {os.path.basename(MASTER)}  shape={mm.shape} dtype={mm.dtype}\n")

    full = np.asarray(mm)
    crop = full[CROP_Y:CROP_Y + CROP_W, CROP_X:CROP_X + CROP_W]

    for label, img in (("WHOLE FRAME", full), ("OWNER'S 1:1 CROP", crop)):
        print(f"=== {label} ===")
        cl = ceilings(img)
        for c, nm in enumerate("RGB"):
            print(f"  {nm} ceiling  max={cl[c][0]:6d}  p99.999={cl[c][1]:9.1f}")
        gc, bc = cl[1][0], cl[2][0]
        print(f"  ARM A: green pins below blue? "
              f"G={gc} vs B={bc} -> {'YES' if gc < bc * 0.95 else 'NO'}")

        seq = bg_by_decile(img)
        print(f"  ARM B: B/G by luminance decile "
              f"{' '.join('%.4f' % v for v in seq)}")
        print(f"         monotone fraction {monotone_frac(seq):.2f}, "
              f"span {seq[0]:.4f} -> {seq[-1]:.4f}"
              f"  ({(seq[-1] / seq[0] - 1) * 100:+.1f}%)")

        frac, n = hue_sign(img)
        print(f"  ARM C: hot pixels with B-G>0: {frac:.3f} over {n} px "
              f"-> {'ONE-SIDED (not interference)' if one_sided(frac) else 'mixed (consistent with interference)'}")
        print()


if __name__ == "__main__":
    main()
