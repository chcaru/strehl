"""COHERENT power against COHERENT power -- the test that separates detail
from noise without assuming anything about flat regions.

WHY.  noisesplit.py shows the free comparators' fine-band excess is largest
where the scene has nothing to resolve (enfuse carries 3.4x strehl's absolute
0.20-0.25 power in FLAT regions and 1.09x in DETAIL ones), which says the excess
is a noise floor.  That reading rests on flat regions being a fair estimate of
the floor inside detailed ones.  This file does not need that assumption.

THE PRIMITIVE is h2h2b's own and is the whole reason the half-stacks exist:
split the 63 frames into two disjoint sets, stack each, and take the real part
of the cross-spectrum.  Photon noise is independent between the halves, so it
contributes zero in expectation; scene structure is the same in both, so it
survives.  Until now only strehl had half-stacks, which made the bound
one-sided.  run_coh.ps1 gives the comparators the same split, so this compares
C against C.

WHAT IT STILL DOES NOT REMOVE, stated before the numbers:
  * noise COMMON to both halves -- fixed-pattern, PRNU, hot pixels -- is
    identical in every frame and survives coherence on BOTH arms
    (V-HEADTOHEAD2 sec.7 disclosed its NOISE_COM arm scoring 6.05).  Both arms
    are built from the same 63 exposures, so both inherit the same common-mode
    noise; that makes it far fairer than before but not absent.
  * deterministic sharpening or ringing is coherent by construction, so
    `C_comp > C_strehl` means "more coherent fine structure", which is
    resolution OR overshoot.  A slanted-edge target would separate those and
    this corpus has none (docs/captures-needed.md sec.30).

REGISTRATION.  The comparator's A, B and full outputs are fused from ONE
alignment pass over all 63 frames (run_coh.ps1), so they are pixel-identical in
geometry and their cross-spectrum needs no registration at all -- which matters,
because at 0.22 cyc/px a single pixel of residual shift is 1.4 rad of phase and
would destroy coherence for a reason unrelated to noise.  Only the strehl->
comparator correspondence is registered, and only to place the crop.

UNITS.  Absolute, not coarse-normalised.  h2.contrast_fft already divides each
crop by its own mean, so exposure and any scalar gain have cancelled and the
numbers are in contrast^2.  gradefree.py measures the tone map between these two
arms at a log-log slope of 0.992, so there is no tone difference left for the
0.05-0.10 normalisation to defend against -- and that normalisation is NOT
neutral here, since the two algorithms differ by ~1.5x in absolute coarse-band
contrast (see noisesplit.py).  Both are reported anyway.

INVOCATION (rule 47).  Reads:
    strehl      C:\\dev\\strehl-out\\V-H2H2\\lin\\113-{full,A,B}-g1.tiff
    comparator  C:\\dev\\strehl-out\\V-LINEAR2\\out\\coh-<tag>-{full,A,B}.tif
Writes nothing.  Prints only.

    python cohfree.py <tag> [nroi=48]      tag in {enfuse, fs15}
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2                                                        # noqa: E402
import rois                                                      # noqa: E402
from h2h2b import Comp, coarse, band_power, cross_bands, load, REF, \
    PEAK_MIN, T, PAD                                             # noqa: E402
from h2free import FREE, BAND                                    # noqa: E402

OUT = r"C:\dev\strehl-out\V-LINEAR2\out"
ARMS = {
    "enfuse": ("enfuse-hardmask.tif", "coh-enfuse-A.tif", "coh-enfuse-B.tif",
               "Hugin align_image_stack + enfuse --hard-mask (GPL)"),
    "fs15": ("coh-fs15-full.tif", "coh-fs15-A.tif", "coh-fs15-B.tif",
             "focus-stack 1.5 merge on Hugin-aligned frames (MIT)"),
}
# MEASURED by geomfree.py, interior maximum required.  enfuse's coherence arm
# IS the primary enfuse arm (run_free.ps1 already fused these same aligned
# frames), so it reuses that fit; coh-fs15 is a different pipeline and gets its
# own.
SCALE = {"enfuse": 1.0050, "fs15": 1.0050}


def main():
    tag = sys.argv[1]
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    full, fa, fb, label = ARMS[tag]
    if SCALE[tag] is None:
        print(f"scale for coherence arm {tag} not measured -- run "
              f"`python geomfree.py coh-{tag}` and paste the interior maximum "
              f"into cohfree.SCALE.")
        return 2
    W = FREE[tag]["weights"]
    paths = [os.path.join(OUT, p) for p in (full, fa, fb)]
    for p in paths:
        if not os.path.exists(p):
            print(f"missing {p} -- run run_coh.ps1 first")
            return 2

    lo = np.array([b[0] for b in h2.BANDS])
    hi = np.array([b[1] for b in h2.BANDS])
    names = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]
    bi = names.index(BAND)

    XF = Comp(dict(path=paths[0], weights=W))
    XA = Comp(dict(path=paths[1], weights=W))
    XB = Comp(dict(path=paths[2], weights=W))
    if not (XF.g.shape == XA.g.shape == XB.g.shape):
        print(f"  RASTERS DISAGREE  full {XF.g.shape} A {XA.g.shape} "
              f"B {XB.g.shape}\n  A cross-spectrum between disagreeing rasters "
              f"measures misregistration, not\n  coherence, and the error runs "
              f"in strehl's favour.  ABANDONED.")
        return 2

    A = load("113-A-g1"); B = load("113-B-g1"); F1 = load("113-full-g1")
    # THE SCALE IS THE MEASURED CONTENT SCALE, NOT THE RASTER RATIO.  For
    # enfuse those disagree -- rasters 7032 vs 7029 is a ratio of 1.0004, while
    # geomfree.py's interior-maximum fit puts the CONTENT at 1.0050 -- because
    # align_image_stack's -m optimises field of view and then remaps, so the
    # canvas size says nothing about the magnification inside it.  Using the
    # raster ratio would mis-size the crop by ~1 px in 200 and smear the very
    # bands under test.  coh-fs15-* is fused from Hugin-aligned frames and does
    # NOT share the fs15 arm's geometry, so it is fitted separately.
    S = SCALE[tag]
    TC = int(round(T / S))
    print("=" * 100)
    print(f"COHERENT vs COHERENT : strehl vs {label}")
    print("=" * 100)
    print(f"  strehl raster {F1.h}x{F1.w}  comparator raster {XF.h}x{XF.w}")
    print(f"  content scale {S:.4f} MEASURED by geomfree.py (interior maximum)"
          f" -> strehl box {T}px, comparator box {TC}px")
    print(f"  comparator full/A/B rasters identical: cross-spectrum needs no "
          f"registration")
    print(f"  pre-registered band {BAND} cyc/px")

    detail, flat, counts = rois.census(F1, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(11)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]

    acc = {k: [] for k in ("Cs", "Ps", "Cx", "Px")}
    used = drop = 0
    for (y, x) in det:
        ca, na = A.crop(y, x, T); cb, nb = B.crop(y, x, T)
        c1, n1 = F1.crop(y, x, T)
        if na or nb or n1:
            drop += 1
            continue
        y0 = int(round(y / S)); x0 = int(round(x / S))
        cf, nc = XF.crop(y0, x0, TC)
        if cf is None or nc:
            drop += 1
            continue
        p, q = coarse(c1), coarse(cf)
        n = min(p.shape[0], q.shape[0])
        dy, dx, pk = h2.integer_shift(p[:n, :n], q[:n, :n], maxshift=6)
        if pk < PEAK_MIN:
            drop += 1
            continue
        y0 += dy * 4; x0 += dx * 4
        cf, n1c = XF.crop(y0, x0, TC)
        cxa, n2c = XA.crop(y0, x0, TC)
        cxb, n3c = XB.crop(y0, x0, TC)
        if any(v is None for v in (cf, cxa, cxb)) or (n1c or n2c or n3c):
            drop += 1
            continue
        Cs = cross_bands(ca, cb)
        Ps = band_power(c1, lo, hi)
        Cx = cross_bands(cxa, cxb)
        Px = band_power(cf, lo * S, hi * S)
        if any(v is None for v in (Cs, Ps, Cx, Px)):
            drop += 1
            continue
        for k, v in zip(("Cs", "Ps", "Cx", "Px"), (Cs, Ps, Cx, Px)):
            acc[k].append(v)
        used += 1
    print(f"\n  ROIs: {used} used, {drop} dropped, {len(det)} offered")
    if used < 8:
        print("  FEWER THAN 8 USABLE ROIs -- ABANDONED, not reported.")
        return 0
    for k in acc:
        acc[k] = np.array(acc[k])

    print(f"\n=== absolute contrast power, sums over {used} ROIs ===")
    print(f"  {'band':>11} {'P strehl':>12} {'C strehl':>12} {'coh frac':>9}   "
          f"{'P comp':>12} {'C comp':>12} {'coh frac':>9}")
    for i, nm in enumerate(names):
        ps = acc["Ps"][:, i].sum(); cs = acc["Cs"][:, i].sum()
        px = acc["Px"][:, i].sum(); cx = acc["Cx"][:, i].sum()
        print(f"  {nm:>11} {ps:12.5g} {cs:12.5g} {cs / ps:9.3f}   "
              f"{px:12.5g} {cx:12.5g} {cx / px:9.3f}")

    print(f"\n=== strehl / comparator, 95% bootstrap CI over ROIs ===")
    print(f"  {'band':>11} {'P_s/P_c':>9} {'CI95':>17}   "
          f"{'C_s/C_c':>9} {'CI95':>17}")
    for i, nm in enumerate(names):
        r1, a1, b1 = h2.bootstrap_ratio(acc["Ps"][:, i], acc["Px"][:, i])
        r2, a2, b2 = h2.bootstrap_ratio(acc["Cs"][:, i], acc["Cx"][:, i])
        mark = "  <== PRE-REGISTERED" if i == bi else ""
        print(f"  {nm:>11} {r1:9.4f} [{a1:6.3f},{b1:6.3f}]   "
              f"{r2:9.4f} [{a2:6.3f},{b2:6.3f}]{mark}")

    r, a, b = h2.bootstrap_ratio(acc["Cs"][:, bi], acc["Cx"][:, bi])
    print(f"\n=== VERDICT at {BAND}, coherent against coherent ===")
    print(f"  C_strehl / C_comp = {r:.4f}  95% CI [{a:.3f}, {b:.3f}]")
    if a > 1.05:
        v = "AHEAD -- strehl carries more COHERENT structure in this band"
    elif b < 0.95:
        v = "BEHIND -- the comparator carries more coherent structure"
    else:
        v = "LEVEL -- CI spans the 5% floor set by the NULL arm's identity bias"
    print(f"  {v}")
    print(f"  floor: gradeatsource.py NULL arm identity bias is 0.8-1.7% "
          f"(0.9918 at {BAND});\n  a difference smaller than that is not a "
          f"difference.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
