"""THE HEAD-TO-HEAD against the FREE FIELD, on the pre-registered band.

WHY THIS FILE EXISTS RATHER THAN AN EDIT TO h2h2b.py
----------------------------------------------------
h2h2b.py is the prior lane's committed instrument and another agent may be
reading it, so it is IMPORTED, not modified.  Every statistic below --
`Comp`, `coarse`, `band_power`, `cross_bands`, `grade`, `load`, `REF`,
`PEAK_MIN`, `T`, `PAD` -- is h2h2b's own.  What is new here is only:

  * a comparator list this project can actually re-run.  Zerene's trial has
    expired and it writes zero bytes (docs/research/V-LINEAR.md sec.1), so
    h2h2b.COMP["113"] can no longer be reproduced by anyone;
  * measured scales from geomfree.py instead of literals;
  * a 95% bootstrap CI on every arm-to-arm ratio, because the brief asks for a
    verdict with a confidence interval beside it;
  * the pre-registered decision applied explicitly, in words, at the end.

THE BAND IS NOT CHOSEN HERE.  It was fixed by bandsignal.py before any
comparator output existed, under the rule committed in PREREGISTRATION.md
(9b192e79).  On this corpus that is 0.20-0.25 cyc/px: the highest-frequency band
whose in-focus/defocused power ratio passes (R = 2.42, CI [1.96, 3.06]).
0.25-0.30 is MARGINAL (1.39) and 0.30-0.48 FAILS -- those bands are noise here
and no verdict is reported on them however the numbers fall.

WHAT IS ONE-SIDED, AND WHICH WAY (inherited from h2h2b, all still true)
----------------------------------------------------------------------
  * `Cn_strehl` is coherent power across disjoint half-stacks: strehl's noise
    contributes zero.  `Pn_comp` is the comparator's signal PLUS its noise.  So
    `Cn_strehl > Pn_comp` is RIGOROUS for strehl and `<=` is INCONCLUSIVE, not
    a loss.
  * `Pn_strehl / Pn_comp` is the symmetric best-effort statistic, and it is what
    the pre-registration names.  Both arms carry their own noise in it.
  * The comparator is handed strehl's OWN linear develops, so demosaic, white
    balance and primaries are identical across arms and the remaining
    difference is the stacking algorithm.  That was the point of V-LINEAR.
  * focus-stack writes 8 bits per channel.  quantfloor.py measures that this
    INFLATES its normalised 0.20-0.25 statistic by +14.6% -- in the
    comparator's favour.  So a strehl win over focus-stack survives it and a
    strehl loss to focus-stack does not.  Stated again in the output.
  * `C` is inflated by noise common to both half-stacks (V-HEADTOHEAD2 sec.7,
    NOISE_COM arm 6.05).  `C` is therefore quoted only as the one-sided bound
    and never as the headline.

INVOCATION (rule 47).  Reads:
    strehl      C:\\dev\\strehl-out\\V-H2H2\\lin\\113-{full,A,B}-g1.tiff
                (render_linear.ps1, STREHL_FULLRES_GATHER=1, binary 740e7056)
    comparators C:\\dev\\strehl-out\\V-LINEAR2\\out\\*.tif  (run_free.ps1)
Writes nothing.  Prints only.

    python h2free.py <tag> [nroi=64]      tag in {enfuse, fs15, fsfork}
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2                                                        # noqa: E402
import rois                                                      # noqa: E402
import h2h2b                                                     # noqa: E402
from h2h2b import Comp, coarse, band_power, cross_bands, grade, load, REF, \
    PEAK_MIN, T, PAD                                             # noqa: E402

OUT = r"C:\dev\strehl-out\V-LINEAR2\out"
W709 = (0.2126, 0.7152, 0.0722)          # inputs are strehl's own linear sRGB,
                                         # so every arm shares BT.709 primaries

# scale = MEASURED by geomfree.py, interior maximum required.  bits = measured
# output bit depth.  Nothing here is a guess; see the report for the runs.
FREE = {
    "enfuse": dict(path=rf"{OUT}\enfuse-hardmask.tif", scale=1.0050, bits=16,
                   label="Hugin align_image_stack + enfuse --hard-mask (GPL)",
                   weights=W709),
    "fs15": dict(path=rf"{OUT}\focusstack-1.5.tif", scale=1.0230, bits=8,
                 label="focus-stack 1.5 upstream (MIT)", weights=W709),
    "fsfork": dict(path=rf"{OUT}\focusstack-fork.tif", scale=None, bits=16,
                   label="focus-stack, owner's local build", weights=W709),
    # Mechanism arm, not a comparator.  Same inputs and same alignment as
    # "enfuse", differing only in --levels=1, which turns off the Burt-Adelson
    # pyramid and makes the blend a straight per-pixel mask.  It exists to test
    # whether enfuse's coarse-band deficit is produced by its own multi-scale
    # blending; see noisesplit.py's absolute-power table.
    "enfuse-lv1": dict(path=rf"{OUT}\enfuse-lv1.tif", scale=1.0050, bits=16,
                       label="enfuse --hard-mask --levels=1 (GPL) [mechanism "
                             "arm, not a comparator]", weights=W709),
    # Second mechanism arm.  focus-stack's merge run on the SAME Hugin-aligned
    # frames enfuse consumed.  Same inputs, same alignment, different merge --
    # so it separates "the Hugin alignment pass costs coarse contrast" from
    # "enfuse's blend costs coarse contrast".
    "coh-fs15": dict(path=rf"{OUT}\coh-fs15-full.tif", scale=1.0050, bits=8,
                     label="focus-stack 1.5 merge on Hugin-aligned frames (MIT)"
                           " [mechanism arm]", weights=W709),
}
BAND = "0.20-0.25"                       # pre-registered, see module docstring
LEVEL = 0.05                             # |ratio-1| below this is LEVEL, from
                                         # the NULL identity bias of 1.0-1.4%


def main():
    tag = sys.argv[1]
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    cfg = FREE[tag]
    if cfg["scale"] is None:
        print(f"scale for {tag} is not filled in -- run `python geomfree.py "
              f"{tag}` first and paste the measured interior maximum.")
        return 2
    if not os.path.exists(cfg["path"]):
        print(f"comparator output missing: {cfg['path']}")
        return 2

    S = cfg["scale"]
    TC = int(round(T / S))
    lo = np.array([b[0] for b in h2.BANDS])
    hi = np.array([b[1] for b in h2.BANDS])
    names = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]
    bi = names.index(BAND)

    print("=" * 100)
    print(f"FREE-FIELD HEAD-TO-HEAD : strehl vs {cfg['label']}")
    print("=" * 100)
    print(f"  scale {S:.4f} MEASURED by geomfree.py (interior maximum) -> "
          f"strehl box {T}px, comparator box {TC}px: same scene area")
    print(f"  reference band {names[REF]} cyc/strehl-px; every arm divided by "
          f"its OWN value there, inside each ROI")
    print(f"  PRE-REGISTERED comparison band: {BAND} cyc/px "
          f"(bandsignal.py R=2.42, CI[1.96,3.06])")
    print(f"  comparator output bit depth: {cfg['bits']}")

    A = load("113-A-g1"); B = load("113-B-g1"); F1 = load("113-full-g1")
    X = Comp(cfg)

    detail, flat, counts = rois.census(F1, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(7)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]

    # ---- registration NULL control: what does "no correspondence" score? ----
    null_pk = []
    for i, (y, x) in enumerate(det[:24]):
        cs, _ = F1.crop(y, x, T)
        yj, xj = det[(i + 7) % len(det)]
        cx, _ = X.crop(int(round(yj / S)), int(round(xj / S)), TC)
        if cx is None:
            continue
        a = coarse(cs); b = coarse(cx)
        n = min(a.shape[0], b.shape[0])
        _, _, pk = h2.integer_shift(a[:n, :n], b[:n, :n], maxshift=6)
        null_pk.append(pk)
    null_pk = np.array(null_pk)
    print(f"\n  NULL registration control ({len(null_pk)} deliberately "
          f"mismatched ROI pairs):\n    peak median "
          f"{np.median(null_pk):.4f}, max {null_pk.max():.4f};  gate "
          f"PEAK_MIN={PEAK_MIN:.2f} is "
          f"{'ABOVE' if PEAK_MIN > null_pk.max() else 'NOT ABOVE'} the null max")

    # ---------------------------- the measurement ---------------------------
    acc = {k: [] for k in ("C1", "P1", "PX", "PG")}
    used = drop_clip_s = drop_clip_x = drop_reg = drop_fft = 0
    peaks = []
    for (y, x) in det:
        ca, na = A.crop(y, x, T); cb, nb = B.crop(y, x, T)
        c1, n1c = F1.crop(y, x, T)
        if na or nb or n1c:
            drop_clip_s += 1
            continue
        y0 = int(round(y / S)); x0 = int(round(x / S))
        cx, ncl = X.crop(y0, x0, TC)
        if cx is None or ncl:
            drop_clip_x += 1
            continue
        aa = coarse(c1); bb = coarse(cx)
        n = min(aa.shape[0], bb.shape[0])
        dy, dx, pk = h2.integer_shift(aa[:n, :n], bb[:n, :n], maxshift=6)
        if pk < PEAK_MIN:
            drop_reg += 1
            continue
        cx, ncl = X.crop(y0 + dy * 4, x0 + dx * 4, TC)
        if cx is None or ncl:
            drop_clip_x += 1
            continue
        C1 = cross_bands(ca, cb)
        P1 = band_power(c1, lo, hi)
        PX = band_power(cx, lo * S, hi * S)
        PG = band_power(grade(c1), lo, hi)
        if any(v is None for v in (C1, P1, PX, PG)):
            drop_fft += 1
            continue
        for k, v in zip(("C1", "P1", "PX", "PG"), (C1, P1, PX, PG)):
            acc[k].append(v)
        peaks.append(pk)
        used += 1

    tot = len(det)
    print(f"\n  ROI partition (must sum to {tot}):")
    for lbl, v in (("used", used), ("dropped, strehl clipped", drop_clip_s),
                   ("dropped, comparator clipped/off-frame", drop_clip_x),
                   ("dropped, registration below gate", drop_reg),
                   ("dropped, FFT degenerate", drop_fft)):
        print(f"    {lbl:<40} {v}")
    s = used + drop_clip_s + drop_clip_x + drop_reg + drop_fft
    print(f"    {'---- total':<40} {s}   {'OK' if s == tot else 'MISMATCH'}")
    assert s == tot
    if used < 8:
        print("\n  FEWER THAN 8 USABLE ROIs -- this pairing is ABANDONED, not "
              "reported as a result.")
        return 0
    peaks = np.array(peaks)
    print(f"  registration peak on used ROIs: median {np.median(peaks):.4f} "
          f"min {peaks.min():.4f} (null max {null_pk.max():.4f})")

    for k in acc:
        acc[k] = np.array(acc[k])

    def shape(v):
        r = np.maximum(v[:, REF:REF + 1], 1e-30)
        return v / r

    n1 = shape(acc["C1"]); p1 = shape(acc["P1"])
    px = shape(acc["PX"]); pg = shape(acc["PG"])

    # ---- GRADE ARM: reproduced from h2h2b, NOT used as this lane's gate ----
    # V-HEADTOHEAD2 sec.4.4 already published this arm FAILING at 189.90% and
    # drew the correct conclusion: coarse-normalisation does not buy
    # grade-invariance.  Reproducing that number here is COMMISSIONING evidence
    # that this file's reuse of h2h2b is faithful, not a new result.
    #
    # It is not the gate for this lane, for two measured reasons:
    #   1. PREREGISTRATION.md sec.4 names gradetest.py as the tone gate, which
    #      measures the ACTUAL tone difference between these two arms instead of
    #      a hypothetical one.  Run it via gradefree.py.
    #   2. h2h2b.grade() clips at 2x the ROI median.  On these LINEAR develops
    #      that hard-clips a median of 10.1% of pixels per ROI (max 25.3%,
    #      measured over 45 ROIs of 113-full-g1).  Clipping is a far stronger
    #      nonlinearity than the "mild S-curve" the arm is described as, and it
    #      is the dominant harmonic generator in the 190% figure.  The arm is
    #      therefore mis-calibrated for linear-light input -- which does not
    #      rescue the grade-invariance claim, it only means this number
    #      overstates how gentle a curve has to be to break it.
    gmax = np.abs(pg.mean(0) / p1.mean(0) - 1).max()
    print(f"\n=== GRADE ARM (inherited from h2h2b, reproduced not re-derived) ===")
    print(f"    worst band deviation under h2h2b's S-curve: {100*gmax:.2f}%  "
          f"(V-HEADTOHEAD2 sec.4.4 published 189.90%)")
    print(f"    That arm's disturbance CLIPS ~10% of pixels on linear input, so "
          f"it is not the\n    gate here.  The gate is gradetest.py via "
          f"gradefree.py, which fits the REAL tone\n    difference between "
          f"these two arms.  Band numbers below are only meaningful if\n"
          f"    that test says tone does not explain the gap.")

    # ------------------------------ the table -------------------------------
    print(f"\n=== strehl / comparator, normalised spectra, 95% bootstrap CI "
          f"over {used} ROIs ===")
    print(f"  {'band':>11} {'Pn_s/Pn_c':>10} {'CI95':>17}   "
          f"{'Cn_s/Pn_c':>10} {'CI95':>17}   band-signal")
    sig = {"0.02-0.05": "PASS", "0.05-0.10": "PASS", "0.10-0.20": "PASS",
           "0.20-0.25": "PASS", "0.25-0.30": "MARGINAL", "0.30-0.40": "noise",
           "0.40-0.48": "noise"}
    for i, nm in enumerate(names):
        r, l1, h1 = h2.bootstrap_ratio(p1[:, i], px[:, i])
        rc, l2, h2q = h2.bootstrap_ratio(n1[:, i], px[:, i])
        mark = "  <== PRE-REGISTERED" if i == bi else ""
        print(f"  {nm:>11} {r:10.4f} [{l1:6.3f},{h1:6.3f}]   "
              f"{rc:10.4f} [{l2:6.3f},{h2q:6.3f}]   {sig[nm]:<9}{mark}")

    r, l1, h1 = h2.bootstrap_ratio(p1[:, bi], px[:, bi])
    rc, l2, h2q = h2.bootstrap_ratio(n1[:, bi], px[:, bi])
    print(f"\n=== VERDICT at the pre-registered band {BAND} ===")
    print(f"  Pn_strehl / Pn_comp = {r:.4f}  95% CI [{l1:.3f}, {h1:.3f}]")
    if l1 > 1.0 and (r - 1) > LEVEL:
        v = "AHEAD -- strehl carries more contrast in this band"
    elif h1 < 1.0 and (1 - r) > LEVEL:
        v = "BEHIND -- the comparator carries more contrast in this band"
    elif l1 <= 1.0 <= h1:
        v = "LEVEL -- the 95% CI includes 1.0"
    else:
        v = f"LEVEL -- |ratio-1| = {abs(r-1)*100:.1f}% is within the {LEVEL*100:.0f}% floor"
    print(f"  {v}")
    print(f"  rigorous one-sided bound Cn_strehl / Pn_comp = {rc:.4f} "
          f"[{l2:.3f}, {h2q:.3f}]"
          f"\n    ({'>1: RIGOROUS strehl win' if l2 > 1 else '<=1: inconclusive, not a loss'})")
    if cfg["bits"] == 8:
        print(f"  BIT-DEPTH CAVEAT: this comparator writes 8 bits.  "
              f"quantfloor.py measures that\n    this inflates its normalised "
              f"{BAND} statistic by +14.6%, i.e. IN ITS FAVOUR.\n    A strehl "
              f"win here survives that; a strehl loss here would not be "
              f"interpretable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
