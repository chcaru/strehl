"""Sharpness evidence that injected structure CANNOT satisfy.

WHY THIS FILE EXISTS
--------------------
V-HALO killed the v1 "not a blur" claim, and it was right to. That claim rested
on `hp_energy` -- summed high-pass energy -- rising rather than falling. But
`hp_energy` is a *magnitude*, and a magnitude cannot tell detail from damage:
the v1 fix injected quantisation discontinuities, a discontinuity is broadband,
and the statistic scored the artefact as sharpness. It rose +16.8% on the flat
crops and +93.6% on `flower-bud flat1` -- inside regions the ROI plan chose
BECAUSE THEY CONTAIN NO STRUCTURE. There is no reading of that number under
which it is measuring detail.

So the replacement may not be another energy. It has to be a statistic that
*injection actively pushes the wrong way*. Two are computed here.

    1. SEAM-EXCLUDED HIGH-PASS ENERGY.
       The fix can only change a pixel it treats. Injected structure therefore
       lives at treatment boundaries. Dilate the treated/untreated transition
       and measure energy only OUTSIDE it. A blur still shows up -- blur is not
       confined to boundaries -- but injection is excluded by construction
       rather than by hoping it is small.

    2. HIGH-PASS CORRELATION AGAINST THE UNTREATED ARM (`hp_ncc`).
       This is the load-bearing one. Correlate the two arms' high-pass bands.
       Real detail is present in BOTH arms and correlates. Blur REMOVES detail
       from one arm, so correlation falls. Injection ADDS structure to one arm
       that has no counterpart in the other, so correlation ALSO falls. It is
       a two-sided instrument: the only way to score well is to reproduce the
       detail that was already there and add nothing that was not.

       `hp_ncc` cannot be gamed by the artefact that broke `hp_energy`. That is
       the entire point, and it is why the ratio of the two is diagnostic:
       energy up WITH correlation down is injection, and nothing else is.

WHAT `hp_ncc` CANNOT DO: it is symmetric, so on its own it says the arms differ
without saying which is better. That is what the energy columns and the ROI
class are for -- a fall in `hp_ncc` inside a FLAT ROI cannot be the fix
recovering detail, because the plan selected that ROI for having none. Read the
three columns together; no one of them is a verdict.

Deliberately NOT reported: any single global scalar over the whole plane.
Plane-averaged statistics have washed out a localised win three separate times
in this build.
"""

import json
import os
import sys

import numpy as np
import tifffile


def read16(path):
    """16-bit RGB TIFF. Never PIL: it silently downconverts 3-channel to 8-bit."""
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: dtype {a.dtype}, expected uint16"
    return a


def luma(a):
    """Camera-native RGB to a single plane. Weights are deliberately flat.

    The measurement path emits camera-native primaries, so BT.709 luma weights
    would be wrong here -- they assume sRGB primaries this file does not have.
    A flat mean makes no claim about colour, which is the honest option when the
    primaries are the sensor's own.
    """
    return a.astype(np.float64).mean(axis=2) / 65535.0


def highpass(p):
    """Laplacian-of-the-box: plane minus its 3x3 box mean, by summed-area table.

    Separable box blur via cumulative sums so the whole plane costs O(n) rather
    than O(n*k^2); the ROIs are small but the seam mask needs the full plane.
    """
    pad = np.pad(p, 1, mode="edge")
    c = pad.cumsum(0).cumsum(1)
    c = np.pad(c, ((1, 0), (1, 0)))
    box = c[3:, 3:] - c[:-3, 3:] - c[3:, :-3] + c[:-3, :-3]
    return p - box / 9.0


def dilate(mask, r):
    """Binary dilation by an (2r+1) square, again by summed area."""
    if r <= 0:
        return mask
    m = mask.astype(np.float32)
    c = np.pad(m, r + 1, mode="constant").cumsum(0).cumsum(1)
    k = 2 * r + 1
    s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return s[: mask.shape[0], : mask.shape[1]] > 0


def ncc(x, y):
    """Zero-mean normalised cross-correlation. 1.0 = identical structure."""
    x = x - x.mean()
    y = y - y.mean()
    d = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / d) if d > 0 else float("nan")


def coherence(d):
    """Lag-1 spatial autocorrelation of the difference between the arms.

    THIS IS THE STATISTIC THAT ADJUDICATES V-HALO'S FINDING, and it exists
    because commissioning showed the other two cannot.

    V-HALO read the flat-ROI `hp_energy` rise as injected structure. But this
    file's own synthetic commissioning found that merely RAISING THE NOISE of a
    flat region produces the same rise -- a +33% noise SD gives +76% high-pass
    energy, because energy goes as variance. And the background noise increase
    of this fix is already measured and already known (+8.9% at v1, which
    predicts +18.6% energy against V-HALO's observed +16.8%). So `hp_energy`
    cannot tell "invented edge" from "noisier background", and neither can
    `hp_ncc`, which both of them push down.

    What separates them is SHAPE, not size. Extra noise is spatially
    incoherent: its lag-1 autocorrelation is ~0. An invented edge, a blotch
    seam or a coverage boundary is spatially COHERENT: neighbouring pixels of
    the difference agree, so the autocorrelation is large.

        d_ac1 ~ 0.0-0.2  the arms differ by NOISE
        d_ac1 > 0.5      the arms differ by STRUCTURE, and in a flat ROI
                         that structure is invented, because the plan chose
                         the ROI for having none

    Reported alongside `d_sd`, the size of the difference, because a large
    coherence on a difference too small to see is not a defect.
    """
    d = d - d.mean()
    v = float((d * d).sum())
    if v <= 0:
        return float("nan")
    h = float((d[:, :-1] * d[:, 1:]).sum()) / v
    w = float((d[:-1, :] * d[1:, :]).sum()) / v
    return 0.5 * (h + w)


def main():
    plan_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\roi-plan.json"
    root = sys.argv[2] if len(sys.argv) > 2 else r"C:\dev\strehl-out\v2ab"
    plan = json.load(open(plan_path))

    print(f"plan  : {plan_path}   (READ ONLY -- never re-derived)")
    print(f"arms  : {root}\\<subject>\\{{off,on}}\\linear.tif")
    print()
    hdr = (
        f"{'subject':<24} {'roi':<8} {'hp_e off':>10} {'hp_e d%':>8} {'seam-ex d%':>11} "
        f"{'hp_ncc':>8} {'d_sd(DN)':>9} {'d_ac1':>7} {'treated%':>9}"
    )
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for subject in sorted(os.listdir(root)):
        off_p = os.path.join(root, subject, "off", "linear.tif")
        on_p = os.path.join(root, subject, "on", "linear.tif")
        if not (os.path.exists(off_p) and os.path.exists(on_p)):
            continue
        if subject not in plan:
            print(f"{subject:<24} NOT IN PLAN -- skipped")
            continue

        off, on = read16(off_p), read16(on_p)
        assert off.shape == on.shape, (off.shape, on.shape)
        lo, ln = luma(off), luma(on)

        # Where the fix actually moved a pixel. This is the treated set as the
        # OUTPUT sees it -- not what the code thinks it treated -- so it cannot
        # disagree with the file. A pixel that moved by less than one 16-bit
        # step is not a treatment, it is rounding.
        moved = np.abs(off.astype(np.int32) - on.astype(np.int32)).max(axis=2) > 1
        # A seam is the BOUNDARY of the moved set: pixels that are near both
        # treated and untreated ground. That band is where a discontinuity
        # between the two can exist at all, so excluding it excludes injection
        # by construction rather than by hoping injection is small.
        seam = dilate(moved, 3) & dilate(~moved, 3)

        ho, hn = highpass(lo), highpass(ln)
        crop = plan[subject]["crop"]

        for cls, pts in plan[subject]["rois"].items():
            for i, (x, y) in enumerate(pts):
                sl = (slice(y, y + crop), slice(x, x + crop))
                a, b = ho[sl], hn[sl]
                m, s = moved[sl], seam[sl]
                e_off = float((a * a).sum())
                e_on = float((b * b).sum())
                keep = ~s
                if keep.sum() > 64:
                    se_off = float((a[keep] ** 2).sum())
                    se_on = float((b[keep] ** 2).sum())
                    sd = 100.0 * (se_on - se_off) / se_off if se_off > 0 else float("nan")
                else:
                    sd = float("nan")
                d = 100.0 * (e_on - e_off) / e_off if e_off > 0 else float("nan")
                r = ncc(a, b)
                diff = (ln[sl] - lo[sl]) * 65535.0
                dsd = float(diff.std())
                ac1 = coherence(diff)
                tf = 100.0 * float(m.mean())
                name = f"{cls}{i + 1}"
                print(
                    f"{subject:<24} {name:<8} {e_off:>10.4f} {d:>+8.1f} {sd:>+11.1f} "
                    f"{r:>8.4f} {dsd:>9.1f} {ac1:>7.3f} {tf:>9.2f}"
                )
                rows.append((subject, cls, name, d, sd, r, tf, dsd, ac1))
        print()

    print("=" * len(hdr))
    print("BY ROI CLASS (median across subjects; flat is the contamination channel)")
    print(
        f"  {'class':<10} {'hp_e d%':>8} {'seam-ex d%':>11} {'hp_ncc':>8} "
        f"{'d_sd(DN)':>9} {'d_ac1':>7} {'treated%':>9}   n"
    )
    for cls in ("edge", "detail", "flat"):
        sel = [r for r in rows if r[1] == cls]
        if not sel:
            continue
        med = lambda j: float(np.nanmedian([r[j] for r in sel]))
        print(
            f"  {cls:<10} {med(3):>+8.1f} {med(4):>+11.1f} {med(5):>8.4f} "
            f"{med(7):>9.1f} {med(8):>7.3f} {med(6):>9.2f}   {len(sel)}"
        )
    print()
    print("READING IT -- no single column is a verdict:")
    print("  hp_e alone         cannot tell detail from damage. It is here only so the")
    print("                     old, void claim can be seen next to its replacement.")
    print("  seam-excluded hp_e blur still shows here; injection cannot, by construction.")
    print("  hp_ncc             falls for BOTH blur and injection. Two-sided on purpose.")
    print("  d_ac1              ~0 = the arms differ by NOISE.  >0.5 = by STRUCTURE.")
    print("                     In a FLAT roi, structure is invented -- the plan chose")
    print("                     that roi for having none.")
    print("  d_sd               how big the difference is at all. A coherent difference")
    print("                     too small to see is not a defect.")


if __name__ == "__main__":
    main()
