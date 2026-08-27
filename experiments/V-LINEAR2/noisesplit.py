"""IS THE COMPARATOR'S FINE-BAND EXCESS DETAIL, OR IS IT NOISE?

THE PROBLEM THIS EXISTS TO SOLVE.  On the pre-registered band 0.20-0.25 cyc/px
both free comparators carry MORE normalised power than strehl (enfuse 1.80x,
focus-stack 1.5 1.99x), and gradefree.py has just shown that tone explains
essentially none of it (fitted slope 0.992, gap explained -0.8%).  So the gap is
real.  It is not yet a resolution result, because exactly three things raise
power in a fine band:

    (a) more resolved detail            <- the only one that is a win
    (b) more noise                      <- enfuse --hard-mask copies pixels from
                                           ONE source frame per region, so its
                                           noise is single-frame; a blended
                                           merge averages some of that away
    (c) sharpening overshoot / ringing  <- deterministic, and NOT separated by
                                           any coherence test, because overshoot
                                           is coherent by construction

THE DISCRIMINATOR, and why it needs no new instrument.  rois.census already
partitions the frame into DETAIL regions (top 30% local contrast) and FLAT
regions (bottom 10%).  A FLAT region is one where the scene itself has almost no
fine structure, so almost all of its 0.20-0.25 power is whatever the stacker put
there.  That gives a clean two-way reading, and it is stated here BEFORE the
numbers:

    ratio_FLAT ~= 1, ratio_DETAIL >> 1   ->  the excess tracks scene detail.
                                            (a).  A real resolution advantage.
    ratio_FLAT ~= ratio_DETAIL >> 1      ->  the excess is present where there is
                                            nothing to resolve.  (b) or (c).
                                            NOT a resolution advantage.
    ratio_FLAT >> ratio_DETAIL           ->  worse still: the excess is
                                            concentrated where the scene is
                                            empty.

REGISTRATION.  band_power is a magnitude-only statistic computed on each crop
independently, so a one- or two-pixel offset changes nothing measurable; only
the cross-spectra in h2free need tight registration.  Flat regions by definition
have too little structure to phase-correlate, so they use the GLOBAL offset
geomfree.py measured.  For enfuse that offset is constant to 0.0 px rms over all
64 probe tiles, which is the strongest global fit this project has recorded.  To
prove the fallback is harmless the DETAIL set is measured BOTH ways -- per-ROI
registration exactly as h2free.py does it, and the same global offset the FLAT
set uses -- and the two are printed side by side.

Every statistic is h2h2b's and h2's, imported unmodified.

INVOCATION (rule 47).  Reads:
    strehl      C:\\dev\\strehl-out\\V-H2H2\\lin\\113-full-g1.tiff
    comparator  C:\\dev\\strehl-out\\V-LINEAR2\\out\\*.tif   (run_free.ps1)
Writes nothing.  Prints only.

    python noisesplit.py <tag> [nroi=40]     tag in {enfuse, fs15, fsfork}
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2                                                        # noqa: E402
import rois                                                      # noqa: E402
from h2h2b import Comp, coarse, band_power, load, REF, PEAK_MIN, T, \
    PAD                                                          # noqa: E402
from h2free import FREE, BAND                                     # noqa: E402


def series(F1, X, pts, S, TC, lo, hi, glob, per_roi):
    """Normalised band spectra for both arms over a list of ROI corners."""
    ps, px, drops = [], [], 0
    for (y, x) in pts:
        cs, ns = F1.crop(y, x, T)
        if ns:
            drops += 1
            continue
        y0 = int(round(y / S))
        x0 = int(round(x / S))
        if per_roi:
            cx, nc = X.crop(y0, x0, TC)
            if cx is None or nc:
                drops += 1
                continue
            a = coarse(cs); b = coarse(cx)
            n = min(a.shape[0], b.shape[0])
            dy, dx, pk = h2.integer_shift(a[:n, :n], b[:n, :n], maxshift=6)
            if pk < PEAK_MIN:
                drops += 1
                continue
            y0 += dy * 4; x0 += dx * 4
        else:
            y0 += glob[0]; x0 += glob[1]
        cx, nc = X.crop(y0, x0, TC)
        if cx is None or nc:
            drops += 1
            continue
        A = band_power(cs, lo, hi)
        B = band_power(cx, lo * S, hi * S)
        if A is None or B is None:
            drops += 1
            continue
        ps.append(A); px.append(B)
    if not ps:
        return None, None, drops
    ps = np.array(ps); px = np.array(px)
    return ps, px, drops


def norm(v):
    return v / np.maximum(v[:, REF:REF + 1], 1e-30)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in FREE:
        print(f"usage: python noisesplit.py <{'|'.join(FREE)}> [nroi]")
        return 2
    tag = sys.argv[1]
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    cfg = FREE[tag]
    if cfg["scale"] is None:
        print(f"scale for {tag} not measured -- run geomfree.py {tag} first.")
        return 2
    S = cfg["scale"]
    TC = int(round(T / S))
    lo = np.array([b[0] for b in h2.BANDS])
    hi = np.array([b[1] for b in h2.BANDS])
    names = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]
    bi = names.index(BAND)

    print("=" * 100)
    print(f"DETAIL vs FLAT : strehl vs {cfg['label']}")
    print("=" * 100)
    print(f"  scale {S:.4f}, strehl box {T}px, comparator box {TC}px")
    print(f"  pre-registered band {BAND} cyc/px; every arm / its own {names[REF]}")

    F1 = load("113-full-g1")
    X = Comp(cfg)
    detail, flat, counts = rois.census(F1, t=T, pad=PAD, flat_frac=0.10)
    print(f"  census: {len(detail)} DETAIL ROIs, {len(flat)} FLAT ROIs")

    glob = (0, 0)

    rng = np.random.default_rng(11)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]
    flt = [flat[i] for i in rng.permutation(len(flat))[:nroi]]

    # The global offset is DERIVED HERE with the very function h2free.py uses
    # for its per-ROI refinement, rather than converted out of geomfree.py's
    # units.  geom.offsets works on 8x block means of a zoomed comparator and
    # h2h2b works on 4x block means of an unzoomed one; the two sign and scale
    # conventions are not obviously the same and guessing between them is the
    # kind of assumption V-HEADTOHEAD2 sec.7 warns about.  Taking the median of
    # the per-ROI shifts that h2free itself computes is self-consistent by
    # construction and needs no conversion at all.
    shifts = []
    for (y, x) in det:
        cs, ns = F1.crop(y, x, T)
        if ns:
            continue
        cx, nc = X.crop(int(round(y / S)), int(round(x / S)), TC)
        if cx is None or nc:
            continue
        a = coarse(cs); b = coarse(cx)
        n = min(a.shape[0], b.shape[0])
        dy, dx, pk = h2.integer_shift(a[:n, :n], b[:n, :n], maxshift=6)
        if pk >= PEAK_MIN:
            shifts.append((dy * 4, dx * 4))
    if not shifts:
        print("  no DETAIL ROI registered -- cannot derive a global offset.")
        return 2
    sh = np.array(shifts)
    glob = (int(np.median(sh[:, 0])), int(np.median(sh[:, 1])))
    print(f"  global offset, median of {len(sh)} per-ROI fits: "
          f"dy {glob[0]:+d} dx {glob[1]:+d} comparator px "
          f"(spread dy {sh[:,0].min():+d}..{sh[:,0].max():+d}, "
          f"dx {sh[:,1].min():+d}..{sh[:,1].max():+d})")

    rows = []
    for lbl, pts, per_roi in (("DETAIL, per-ROI registration", det, True),
                              ("DETAIL, global offset only", det, False),
                              ("FLAT,   global offset only", flt, False)):
        ps, px, drops = series(F1, X, pts, S, TC, lo, hi, glob, per_roi)
        if ps is None:
            print(f"\n  {lbl}: no usable ROIs ({drops} dropped) -- ABANDONED")
            continue
        n = len(ps)
        r = []
        for i in range(len(names)):
            v, l, h = h2.bootstrap_ratio(norm(px)[:, i], norm(ps)[:, i])
            r.append((v, l, h))
        rows.append((lbl, n, drops, r, ps, px))

    print(f"\n=== comparator / strehl, normalised power, 95% bootstrap CI ===")
    print(f"  (>1 means the COMPARATOR carries more power in that band)")
    hdr = "  " + " ".join(f"{n:>12}" for n in names)
    print(f"  {'set':<30}{'n':>4}" + hdr)
    for lbl, n, drops, r, _, _ in rows:
        cells = " ".join(f"{v:12.3f}" for v, _, _ in r)
        print(f"  {lbl:<30}{n:>4}  {cells}")

    # ---------------- the same ratios WITHOUT the coarse normalisation -------
    # h2h2b divides every arm by its own 0.05-0.10 power.  That was a defence
    # against the tone confound: with a graded comparator the absolute contrast
    # scale is meaningless, so only the SHAPE of the spectrum can be compared.
    # Here the confound is gone by construction -- gradefree.py fits a tone
    # slope of 0.992 between these two arms -- and h2.contrast_fft already
    # divides each crop by its own mean, so every scalar gain has cancelled and
    # the absolute band powers are in comparable contrast^2 units.
    #
    # It now matters, because the reference band is NOT neutral between these
    # two algorithms: strehl carries about 1.5x enfuse's absolute 0.05-0.10
    # power, so dividing by it inflates every fine band of the comparator's
    # spectrum by that factor before any comparison is made.  Both tables are
    # printed and the difference between them is part of the result.
    print(f"\n=== comparator / strehl, ABSOLUTE contrast power (no 0.05-0.10 "
          f"normalisation) ===")
    print(f"  {'set':<30}{'n':>4}" + hdr)
    absrows = []
    for lbl, n, drops, _, ps, px in rows:
        rr = [h2.bootstrap_ratio(px[:, i], ps[:, i]) for i in range(len(names))]
        absrows.append((lbl, rr))
        print(f"  {lbl:<30}{n:>4}  " + " ".join(f"{v:12.3f}" for v, _, _ in rr))
    for lbl, rr in absrows:
        v, l, h = rr[bi]
        print(f"  {lbl:<30} {BAND}: {v:6.3f}  CI95 [{l:.3f}, {h:.3f}]")
    print()
    for lbl, n, drops, r, _, _ in rows:
        v, l, h = r[bi]
        print(f"  {lbl:<30} {BAND}: {v:6.3f}  CI95 [{l:.3f}, {h:.3f}]   "
              f"({drops} ROIs dropped)")

    # ---- the reading, fixed in the docstring before any of this was run ----
    if len(rows) >= 3:
        rd = rows[0][3][bi][0]          # DETAIL, per-ROI
        rdg = rows[1][3][bi][0]         # DETAIL, global offset
        rf = rows[2][3][bi][0]          # FLAT
        print(f"\n=== READING (criterion fixed in this file's docstring) ===")
        print(f"  registration control: DETAIL per-ROI {rd:.3f} vs DETAIL "
              f"global {rdg:.3f} -> "
              f"{'agree, global offset is harmless' if abs(rd - rdg) < 0.05 * rd else 'DISAGREE, FLAT numbers are suspect'}")
        if rf >= 0.8 * rd:
            print(f"  FLAT {rf:.3f} is not below DETAIL {rd:.3f}: the excess is "
                  f"present where the scene\n  has nothing to resolve.  This is "
                  f"NOISE or OVERSHOOT, not resolution.")
        elif rf <= 1.1:
            print(f"  FLAT {rf:.3f} ~ 1 while DETAIL {rd:.3f} > 1: the excess "
                  f"tracks scene detail.\n  Consistent with a real resolution "
                  f"advantage for the comparator.")
        else:
            print(f"  FLAT {rf:.3f} sits between 1 and DETAIL {rd:.3f}: MIXED. "
                  f"Part of the excess is\n  noise/overshoot and part may be "
                  f"detail; this alone does not decide it.")

        # absolute fine-band power in flat regions == each stacker's own noise
        # floor, in the band, with the scene contributing almost nothing.
        _, _, _, _, psd, pxd = rows[0]
        _, _, _, _, psf, pxf = rows[2]
        print(f"\n  absolute {BAND} band power, medians over ROIs:")
        print(f"    {'':<12}{'DETAIL':>14}{'FLAT':>14}{'FLAT/DETAIL':>14}")
        for nm, d, f in (("strehl", psd, psf), ("comparator", pxd, pxf)):
            md = np.median(d[:, bi]); mf = np.median(f[:, bi])
            print(f"    {nm:<12}{md:14.6g}{mf:14.6g}{mf / max(md, 1e-30):14.3f}")
        ms = np.median(psd[:, bi]) - np.median(psf[:, bi])
        mc = np.median(pxd[:, bi]) - np.median(pxf[:, bi])
        print(f"    DERIVED, not measured: subtracting each arm's own FLAT "
              f"floor from its DETAIL power\n    leaves comparator/strehl = "
              f"{mc / ms if ms > 0 else float('nan'):.3f}.  This assumes the "
              f"floor is the same in\n    DETAIL regions as in FLAT ones, "
              f"which is only true if their light levels match:")
        for nm, d, f in (("strehl", psd, psf), ("comparator", pxd, pxf)):
            print(f"      {nm:<12} 0.05-0.10 reference power  DETAIL "
                  f"{np.median(d[:, REF]):.6g}  FLAT {np.median(f[:, REF]):.6g}")
        print(f"    The half-stack coherence measurement is the one that does "
              f"not need that\n    assumption; this line is a cross-check on "
              f"it, not a substitute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
