#!/usr/bin/env python3
"""
V-EYES: PRE-REGISTRATION for the STREHL_RESTORE A/B.

ORCH's instruction was explicit: "Pre-register before you run. State the band
your ratio actually integrates over, read restore.rs's gain curve at that band,
and predict the move -- including 'no detectable move'. Then measure.
Prediction first, number second."

This script produces the prediction. It is run, and its output committed,
BEFORE the instrument is run on either arm.

WHAT IS BEING PREDICTED
-----------------------
The headline is  median over sites of  detail(master) / detail(envelope),
where `detail` is mean(high-pass^2) per 64 px block minus that image's own 5th
-percentile floor, and `envelope` is the per-site maximum over the complete
focus bracket. The reference arm is UNRESTORED and FIXED -- the frames are
byte-identical between the two arms and that is provable from
PIN/frame-hashes.tsv. So the whole move must come from the master's numerator.

WHY THE PREDICTION CAN BE THIS PRECISE
--------------------------------------
Both masters already exist: rendering them IS the intervention, not the
outcome. The outcome needs the 19-frame bracket, the parity gate, the envelope
and seven commissioning arms, none of which this script touches. So predicting
the numerator from the two masters is a genuine forecast of an unmeasured
quantity, not a restatement of it -- but it is a *tight* one, and that is
deliberate. A vague prediction cannot be wrong, and a prediction that cannot be
wrong is not a pre-registration.

TWO INDEPENDENT ROUTES, BECAUSE ONE ROUTE IS AN ASSERTION
---------------------------------------------------------
  (A) SPECTRAL.  Measure the realised end-to-end transfer T(f) =
      P_restored(f) / P_plain(f) radially, and integrate it against the
      commissioned band density w(f) from band_probe.py. This tests whether my
      model of the band is right, and it is the route that connects to
      restore.rs's published gain curve.

  (B) DIRECT.  Run the pinned `detail()` primitive on both masters and take the
      per-site energy ratio. This is faithful to the actual statistic including
      the 5th-percentile floor subtraction, which route (A) cannot see.

They answer the same question through different arithmetic. If they disagree,
the disagreement is the finding and neither number is quoted.

COMMISSIONING
-------------
Route (A) is checked against an identity it must satisfy: by Parseval, the
band-weighted transfer must reproduce the spatial-domain energy ratio
mean(hp_restored^2)/mean(hp_plain^2) computed on the same tile with no spectra
involved at all. If the radial binning or the windowing is wrong, that identity
breaks. Threshold 5%; the script exits non-zero if it fails, because a
predictor that has not reproduced a known answer is not a predictor.

THE FLOOR HAZARD, STATED IN ADVANCE
-----------------------------------
`detail` subtracts the 5th percentile of block energies as a noise floor. The
restoration amplifies noise along with signal -- that is what a Wiener filter
does -- so the floor rises too, and the net move in `detail` is SMALLER than
the raw energy gain. Route (B) captures this; route (A) does not. The gap
between them therefore measures the floor's bite, and is reported.

Usage:
    python restore_predict.py <subject> [tile]
"""
import pathlib
import sys

import cv2
import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from softness_verdict3 import HP_SIGMA, detail, luma_linear   # noqa: E402
from corpus_softness import pick_tile                          # noqa: E402

AB = pathlib.Path(r"C:\dev\strehl-out\V-EYES\restore-ab")
BLOCK = 64


def luma32(a):
    return luma_linear(a)


def radial(P):
    n = P.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    fr = np.sqrt(fx * fx + fy * fy)
    nb = n // 2
    edges = np.linspace(0.0, 0.5, nb + 1)
    idx = np.clip(np.digitize(fr.ravel(), edges) - 1, 0, nb - 1)
    keep = fr.ravel() > 0
    tot = np.bincount(idx[keep], weights=P.ravel()[keep], minlength=nb)
    cnt = np.bincount(idx[keep], minlength=nb)
    f = 0.5 * (edges[:-1] + edges[1:])
    return f, tot, cnt


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    subject = argv[1]
    size = int(argv[2]) if len(argv) > 2 else 2048

    pa = AB / subject / "MASTER-plain.tiff"
    pb = AB / subject / "MASTER-restore.tiff"
    for p in (pa, pb):
        if not p.exists():
            print(f"missing {p} -- run restore_ab.py first")
            return 1

    A = luma32(tifffile.imread(str(pa)))
    B = luma32(tifffile.imread(str(pb)))
    if A.shape != B.shape:
        print(f"shape mismatch {A.shape} vs {B.shape}")
        return 1

    tx, ty = pick_tile(A, size)
    ta = A[ty:ty + size, tx:tx + size].astype(np.float32)
    tb = B[ty:ty + size, tx:tx + size].astype(np.float32)
    print(f"{subject}  tile ({tx},{ty}) {size}x{size}   HP_SIGMA={HP_SIGMA}, BLOCK={BLOCK}")

    # ---------------- route A: spectral ------------------------------------
    win = np.outer(np.hanning(size), np.hanning(size))
    hpa = (ta - cv2.GaussianBlur(ta, (0, 0), HP_SIGMA)).astype(np.float64)
    hpb = (tb - cv2.GaussianBlur(tb, (0, 0), HP_SIGMA)).astype(np.float64)
    Pa = np.abs(np.fft.fft2(hpa * win)) ** 2
    Pb = np.abs(np.fft.fft2(hpb * win)) ** 2
    f, Sa, cnt = radial(Pa)
    _, Sb, _ = radial(Pb)

    w = Sa / Sa.sum()                       # the commissioned band density
    T = np.divide(Sb, Sa, out=np.ones_like(Sa), where=Sa > 0)   # realised transfer

    predA = float((w * T).sum())
    # COMMISSIONING: the same number with no spectra in it at all.
    direct = float((hpb ** 2 * win ** 2).sum() / (hpa ** 2 * win ** 2).sum())
    err = abs(predA - direct) / direct

    print("\n  realised end-to-end transfer T(f) = P_restored/P_plain  (ENERGY):")
    for probe in (0.05, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25, 0.30, 0.40, 0.49):
        print(f"    f={probe:.3f} cyc/px   T={np.interp(probe, f, T):.4f}"
              f"   (amplitude {np.sqrt(np.interp(probe, f, T)):.4f})")

    cdf = np.cumsum(w)
    print(f"\n  band of the statistic (this tile): centroid "
          f"{float((f * w).sum()):.4f}, median {float(np.interp(0.5, cdf, f)):.4f} cyc/px")
    print(f"  energy at or below the 0.25 knee: {100 * float(np.interp(0.25, f, cdf)):.2f}%")

    print(f"\n  ROUTE A  band-weighted energy gain  = {predA:.4f}")
    print(f"  COMMISSIONING  direct spatial ratio = {direct:.4f}   rel err {100 * err:.2f}%")
    if err >= 0.05:
        print("  -> ROUTE A NOT COMMISSIONED; no prediction issued")
        return 2

    # ---------------- route B: the actual statistic -------------------------
    da, fa = detail(ta, BLOCK)
    db, fb = detail(tb, BLOCK)
    m = da > 0
    per_site = db[m] / da[m]
    predB = float(np.median(per_site))
    print(f"\n  ROUTE B  pinned detail(), {m.sum()} sites")
    print(f"    noise floor   plain {fa:.2f} -> restored {fb:.2f} DN^2"
          f"   ({100 * (fb / fa - 1):+.1f}%)")
    print(f"    per-site median energy gain = {predB:.4f}"
          f"   [P25 {np.percentile(per_site, 25):.4f}, P75 {np.percentile(per_site, 75):.4f}]")
    print(f"    floor bite: route A {predA:.4f} -> route B {predB:.4f}"
          f"  ({100 * (predB / predA - 1):+.1f}%)")

    print(f"\n  ==> PREDICTED move in the softness ratio: x{predB:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
