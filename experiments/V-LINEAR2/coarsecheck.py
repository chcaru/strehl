"""WHICH ARM IS WRONG AT THE COARSE BANDS?  The input frames are the referee.

THE ANOMALY.  noisesplit.py measures, in ABSOLUTE contrast units over DETAIL
ROIs, comparator/strehl = 0.708 at 0.02-0.05 and 0.682 at 0.05-0.10.  enfuse
carries about 30% less coarse-scale contrast than strehl from the SAME 63
frames.  That is far too large to be tone -- gradefree.py fits the tone map
between these two arms at a log-log slope of 0.992 -- so one of the two
stackers is changing coarse structure, and which one it is decides how to read
every normalised number in this lane.  h2h2b divides every spectrum by its own
0.05-0.10 power, so a 30% coarse deficit becomes a 1.5x fine-band INFLATION for
whichever arm has it, before any comparison happens.

THE REFEREE.  Both stackers were fed the same frames, so the frames themselves
say what the scene's coarse contrast is.  This works only if the coarse bands
are focus-independent, which is checkable and is checked first: 0.02-0.10
cyc/px is a period of 10-50 px, and the defocus in this stack is a few px, so
every frame should report nearly the same coarse contrast in the same ROI.  The
spread across frames is printed BEFORE the verdict, and if it is large the test
is abandoned rather than interpreted.

READING, fixed here before the numbers:
    strehl ~ frames, comparator < frames  ->  the comparator LOSES coarse
                                              contrast; strehl is the honest arm
                                              and the normalised table flatters
                                              the comparator.
    comparator ~ frames, strehl > frames  ->  strehl ADDS coarse contrast it was
                                              not given; the normalised table is
                                              closer to right and strehl's merge
                                              is boosting.
    both > frames                         ->  both boost; report both figures.

The frames are read through h2.Render exactly as strehl's own output is, so the
same luma, the same window, the same Parseval normalisation apply to all three.

INVOCATION (rule 47).  Reads:
    strehl      C:\\dev\\strehl-out\\V-H2H2\\lin\\113-full-g1.tiff
    frames      C:\\dev\\strehl-out\\V-LINEAR\\lintiff\\DSC000NN.tif
    comparator  C:\\dev\\strehl-out\\V-LINEAR2\\out\\*.tif
Writes nothing.  Prints only.

    python coarsecheck.py <tag> [nroi=24]     tag in {enfuse, fs15, fsfork}
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
from h2free import FREE                                          # noqa: E402

LIN = r"C:\dev\strehl-out\V-LINEAR\lintiff"
FRAMES = [8, 16, 24, 32, 40, 48, 56]


def main():
    tag = sys.argv[1]
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    cfg = FREE[tag]
    S = cfg["scale"]
    TC = int(round(T / S))
    lo = np.array([b[0] for b in h2.BANDS])
    hi = np.array([b[1] for b in h2.BANDS])
    names = [f"{a:.2f}-{b:.2f}" for a, b in h2.BANDS]

    F1 = load("113-full-g1")
    X = Comp(cfg)
    fr = [h2.Render(os.path.join(LIN, f"DSC{n:05d}.tif"),
                    name=f"DSC{n:05d}", linear=True) for n in FRAMES]
    print("=" * 100)
    print(f"COARSE-BAND REFEREE : strehl vs {cfg['label']} vs the input frames")
    print("=" * 100)
    print(f"  {len(fr)} input frames {FRAMES}, strehl box {T}px, "
          f"comparator box {TC}px at scale {S:.4f}")

    detail, flat, counts = rois.census(F1, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(11)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]

    ps, px, pf = [], [], []
    spreads = []
    used = drop = 0
    for (y, x) in det:
        c1, n1 = F1.crop(y, x, T)
        if n1:
            drop += 1
            continue
        y0 = int(round(y / S)); x0 = int(round(x / S))
        cx, nc = X.crop(y0, x0, TC)
        if cx is None or nc:
            drop += 1
            continue
        a, b = coarse(c1), coarse(cx)
        n = min(a.shape[0], b.shape[0])
        dy, dx, pk = h2.integer_shift(a[:n, :n], b[:n, :n], maxshift=6)
        if pk < PEAK_MIN:
            drop += 1
            continue
        cx, nc = X.crop(y0 + dy * 4, x0 + dx * 4, TC)
        if cx is None or nc:
            drop += 1
            continue
        A = band_power(c1, lo, hi)
        B = band_power(cx, lo * S, hi * S)
        # every input frame, same ROI, same box as strehl (the frames share
        # strehl's raster: strehl reads them, it does not resample the canvas)
        F = []
        for r in fr:
            cc, ncc = r.crop(y, x, T)
            if ncc:
                continue
            v = band_power(cc, lo, hi)
            if v is not None:
                F.append(v)
        if A is None or B is None or len(F) < 3:
            drop += 1
            continue
        F = np.array(F)
        ps.append(A); px.append(B); pf.append(np.median(F, 0))
        spreads.append(F[:, :2].std(0) / np.maximum(F[:, :2].mean(0), 1e-30))
        used += 1

    print(f"\n  ROIs: {used} used, {drop} dropped")
    if used < 8:
        print("  FEWER THAN 8 USABLE ROIs -- ABANDONED.")
        return 0
    ps = np.array(ps); px = np.array(px); pf = np.array(pf)
    sp = np.array(spreads)

    print(f"\n  PRECONDITION: coarse bands must be focus-independent.")
    print(f"    frame-to-frame relative spread of band power, median over ROIs:"
          f"\n      0.02-0.05  {np.median(sp[:, 0]) * 100:5.1f}%"
          f"      0.05-0.10  {np.median(sp[:, 1]) * 100:5.1f}%")
    ok = np.median(sp[:, 1]) < 0.15
    print(f"    {'OK -- a single frame is a valid coarse reference' if ok else 'TOO LARGE -- the frames disagree; this test is ABANDONED'}")
    if not ok:
        return 0

    print(f"\n=== absolute contrast power vs the input frames, 95% bootstrap "
          f"CI over {used} ROIs ===")
    print(f"  {'band':>11} {'strehl/frames':>15} {'CI95':>17}   "
          f"{'comp/frames':>15} {'CI95':>17}")
    for i, nm in enumerate(names):
        r1, a1, b1 = h2.bootstrap_ratio(ps[:, i], pf[:, i])
        r2, a2, b2 = h2.bootstrap_ratio(px[:, i], pf[:, i])
        print(f"  {nm:>11} {r1:15.4f} [{a1:6.3f},{b1:6.3f}]   "
              f"{r2:15.4f} [{a2:6.3f},{b2:6.3f}]")

    rs = h2.bootstrap_ratio(ps[:, REF], pf[:, REF])[0]
    rx = h2.bootstrap_ratio(px[:, REF], pf[:, REF])[0]
    print(f"\n=== READING at the reference band {names[REF]} "
          f"(criterion fixed in this file's docstring) ===")
    print(f"  strehl / frames     {rs:.3f}")
    print(f"  comparator / frames {rx:.3f}")
    if abs(rs - 1) < 0.10 and rx < 0.90:
        print(f"  The COMPARATOR loses coarse contrast; strehl matches the "
              f"frames it was given.\n  Dividing by each arm's own 0.05-0.10 "
              f"power therefore INFLATES the comparator's\n  fine bands by "
              f"~{1 / rx:.2f}x before any comparison is made.")
    elif abs(rx - 1) < 0.10 and rs > 1.10:
        print(f"  STREHL adds coarse contrast it was not given "
              f"({rs:.2f}x the frames).  The coarse\n  normalisation is closer "
              f"to fair than the absolute comparison, and strehl's merge\n"
              f"  is boosting at coarse scales.")
    else:
        print(f"  Neither arm matches the frames cleanly; report both ratios "
              f"and draw no\n  conclusion about which normalisation is fair.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
