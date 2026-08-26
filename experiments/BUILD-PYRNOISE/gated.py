"""Why the arm-vs-arm ratio survives a failed admission test, tested rather than asserted.

`diagnose.py` produced the result that overturns my report to the orchestrator:
across 400 windows the claim's own Laplacian ratio tracks the BINARY'S OWN
n_eff map at corr +0.998 with a median deviation of +0.6%, and the admission
ratio predicts that deviation at corr -0.077 -- i.e. not at all. The claim is
measuring noise. My mechanism does not bite.

The explanation I now owe, and which this file tests:

  THE ADMISSION TEST MEASURES VARIANCE ACROSS THE WHOLE BRACKET. THE MERGE
  NEVER AVERAGES THE WHOLE BRACKET. On a 182-frame focus sweep, the temporal
  sd at a pixel is dominated by the ~170 frames in which that pixel is wildly
  out of focus. `--gate 0` elects the focus WINNER, and `--gate 2` averages
  only frames within the gate of the winner. Both arms therefore see the same
  small, near-winner subset of the bracket, and the bracket-wide
  non-stationarity that the admission test correctly reports is a variance
  NEITHER ARM EVER TOUCHES.

  A single unstacked frame is different in kind: it IS an arbitrary member of
  the bracket, out of focus at that patch in most draws. So for an
  arm-vs-SINGLE-FRAME ratio the bracket-wide non-stationarity is exactly the
  right thing to worry about, and admission is the right gate. For an
  arm-vs-arm ratio between two merges of the same bracket it is not.

THE FALSIFIABLE PREDICTION. Recompute the admission ratio using only the k
frames that are SHARPEST at each pixel -- an approximation of the frames the
merge actually combines. If the explanation is right, the gated ratio must fall
towards 1 while the bracket-wide ratio stays high. If it does not fall, the
explanation is wrong and the agreement with n_eff needs a different account.

Also here: `diagnose.py`'s +0.998 correlation could in principle be an artifact
of a trivial cluster -- most windows on this subject sit at n_eff ~ 1 where
both arms are nearly the same image and both numbers are ~0.92 by default. So
the deviation is re-binned BY PREDICTED RATIO, where the informative windows
are, instead of by admission.
"""

import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

import admission
import pyrnoise as pn
from claim_roi import hp_sigma, F

CLAIM = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\claim")
RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\renders")


def sharpness(a, r=4):
    """Per-pixel local focus response: smoothed squared Laplacian.

    A stand-in for the crate's regularised focus field, deliberately crude --
    it only has to rank frames at a pixel well enough to identify the near-
    winner subset, and the conclusion is checked across a sweep of k so it does
    not hinge on the ranking being exact.
    """
    lap = np.zeros_like(a)
    lap[1:-1, 1:-1] = (4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1]
                       - a[1:-1, :-2] - a[1:-1, 2:])
    return uniform_filter(lap * lap, size=2 * r + 1, mode="reflect")


def gated_admission(imgs, frames, roi, ks=(3, 6, 12, 24)):
    """Admission using only the k sharpest frames AT EACH PIXEL.

    Returns {k: (ratio, temporal, spatial)} plus the ungated reading at k=all.
    The spatial term is unchanged -- it is a within-frame estimate and does not
    depend on which frames are chosen -- so the whole movement is in the
    temporal term, which is the term the explanation is about.
    """
    pad = pn.BOX
    x, y, w, h = roi
    big = np.stack([imgs[f][y - pad:y + h + pad, x - pad:x + w + pad].astype(np.float64)
                    for f in frames])
    core = big[:, pad:-pad, pad:-pad]
    sh = np.stack([sharpness(b) for b in big])[:, pad:-pad, pad:-pad]
    order = np.argsort(-sh, axis=0)          # sharpest first, per pixel
    spatial = float(np.mean([pn.hp_sd(b) for b in big]))
    out = {}
    for k in ks:
        if k > len(frames):
            continue
        sel = np.take_along_axis(core, order[:k], axis=0)
        out[k] = (float(sel.std(axis=0, ddof=1).mean()) / spatial,
                  float(sel.std(axis=0, ddof=1).mean()), spatial)
    allt = float(core.std(axis=0, ddof=1).mean())
    out["all"] = (allt / spatial, allt, spatial)
    return out


def gated_mosaic(imgs, frames, roi, k=6, trials=5, rng=None):
    """The mosaic simulation, restricted to the k sharpest frames per pixel.

    `--gate 0` does not draw an arbitrary frame; it draws the focus winner. A
    mosaic assembled from an arbitrary draw over the whole bracket therefore
    over-states the content term by however much the bracket is out of focus.
    Drawing instead from each pixel's own k sharpest frames is the honest
    stand-in, and the difference between the two is the size of the error in
    `diagnose.py`'s block-1 figure.
    """
    rng = rng or np.random.default_rng(7)
    pad = pn.BOX
    x, y, w, h = roi
    big = np.stack([imgs[f][y - pad:y + h + pad, x - pad:x + w + pad].astype(np.float64)
                    for f in frames])
    sh = np.stack([sharpness(b) for b in big])
    order = np.argsort(-sh, axis=0)
    top = np.take_along_axis(big, order[:k], axis=0)
    s_mean = pn.hp_sd(top.mean(axis=0))
    rs = []
    for _ in range(trials):
        pick = rng.integers(0, k, size=big.shape[1:])
        mos = np.take_along_axis(top, pick[None], axis=0)[0]
        rs.append(s_mean / pn.hp_sd(mos))
    return float(np.mean(rs)), 1.0 / np.sqrt(k)


def main():
    d = RENDERS / "leaf-2-cpl"
    frames = sorted(p.stem for p in d.glob("frame*.tif"))
    imgs = {f: pn.green(d / f"{f}.tif") for f in frames}
    print("=" * 78)
    print("WHY AN ARM-VS-ARM RATIO SURVIVES A FAILED ADMISSION TEST")
    print("=" * 78)
    print(f"leaf-2-cpl, {len(frames)} single frames of 182, pinned binary b9b6921e")

    print("\nF. GATED ADMISSION -- restrict the temporal sd to the frames a merge USES")
    print("   The spatial term is a within-frame estimate and is identical in every")
    print("   row; the whole movement is in the temporal term.")
    rois = {"claim patch  (912,384 full-res)": (292, 500, 100, 100),
            "pinned patch (1344,368 full-res)": (284, 702, 100, 100)}
    res = {}
    for lbl, roi in rois.items():
        g = gated_admission(imgs, frames, roi)
        res[lbl] = {str(k): v for k, v in g.items()}
        print(f"\n   {lbl}   plane ROI {roi}")
        print(f"      {'frames used':<24}{'temporal':>10}{'spatial':>10}{'ratio':>9}   verdict")
        for k in ("all", 24, 12, 6, 3):
            if k not in g:
                continue
            r, t, s = g[k]
            lab = f"whole bracket ({len(frames)})" if k == "all" else f"{k} sharpest per pixel"
            print(f"      {lab:<24}{t:10.2f}{s:10.2f}{r:9.3f}   "
                  f"{'PASS' if r <= admission.BAR else 'FAIL'}")

    print("\nG. THE MOSAIC SIMULATION, DRAWN FROM THE FRAMES SELECTION ACTUALLY USES")
    for lbl, roi in rois.items():
        print(f"   {lbl}")
        for k in (3, 6, 12):
            r, ideal = gated_mosaic(imgs, frames, roi, k=k)
            print(f"      top-{k:<2} mosaic / top-{k:<2} mean = {r:.4f}x"
                  f"   against 1/sqrt({k}) = {ideal:.4f}x   inflation {ideal / r:.2f}x")

    print("\nH. IS THE +0.998 CORRELATION A TRIVIAL-CLUSTER ARTIFACT?")
    rows = json.load(open(CLAIM / "_diagnosis.json"))["rows"]
    A = np.array([r[0] for r in rows])
    M = np.array([r[1] for r in rows])
    P = np.array([r[2] for r in rows])
    dev = np.log(M / P)
    print(f"   re-binned by the TOOL'S PREDICTED ratio, where the informative windows are:")
    print(f"   {'predicted band':<18}{'n':>5}{'measured med':>14}{'predicted med':>15}"
          f"{'dev med':>10}{'adm med':>9}")
    for lo, hi in ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.95), (0.95, 1.1)):
        k = (P >= lo) & (P < hi)
        if k.sum() == 0:
            continue
        print(f"   [{lo:.2f},{hi:.2f})      {k.sum():5d}{np.median(M[k]):14.4f}"
              f"{np.median(P[k]):15.4f}{np.median(dev[k]):+10.3f}{np.median(A[k]):9.2f}")
    inf = P < 0.8
    if inf.sum() >= 3:
        print(f"   restricted to the {inf.sum()} INFORMATIVE windows (predicted < 0.80):")
        print(f"     corr(tool prediction, measured) {np.corrcoef(P[inf], M[inf])[0, 1]:+.3f}")
        print(f"     corr(admission, dev)            {np.corrcoef(A[inf], dev[inf])[0, 1]:+.3f}")
        print(f"     median |dev|                    {np.median(np.abs(dev[inf])) * 100:.1f}%")
    print(f"   predicted ratio spans {P.min():.3f}..{P.max():.3f}, measured {M.min():.3f}..{M.max():.3f}")

    json.dump(res, open(CLAIM / "_gated.json", "w"), indent=1, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())
