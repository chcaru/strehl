"""S2b -- re-select the flat control against ALL 299 frames.

S2 picked windows from 20 evenly spaced frames. S3 then showed that
`ROI-FLAT` peaks at frame 103 with 61.8x focus contrast and a 7-frame FWHM:
the 20-frame scan (stride ~16) stepped straight over its focus peak, so the
"flat" control was really a narrow in-focus feature that the coarse scan
never saw sharp. That is an aliasing failure in the selector, not in the
metric, and it is reported as a control that failed.

This pass computes, for every frame, a decimated map of local high-pass
energy and keeps the RUNNING PER-PIXEL MAXIMUM over the whole stack. A window
whose max-over-frames detail is at the noise floor has no in-focus content at
any point in the stack -- that is the flat control rule 9 asks for.

It also re-reads the detail candidates with the same full-stack statistic, so
the drift stratification is chosen on max-over-299 rather than max-over-20.
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m95lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
DEC = 8  # decimation of the detail map
WIN = 512
STRIDE = 256
BORDER = 64


def _one(path):
    rf = L.decode_raw(path)
    g = L.green_mean_plane(rf.cfa).astype(np.float64) - 512.0
    d = g - L.gaussian_blur(g, 2.0)
    e = d * d
    clip = (rf.cfa >= 15360).astype(np.float32)
    h, w = e.shape
    hh, ww = (h // DEC) * DEC, (w // DEC) * DEC
    det = e[:hh, :ww].reshape(hh // DEC, DEC, ww // DEC, DEC).mean(axis=(1, 3))
    ch, cw = (clip.shape[0] // (2 * DEC)) * (2 * DEC), (clip.shape[1] // (2 * DEC)) * (2 * DEC)
    cl = clip[:ch, :cw].reshape(ch // (2 * DEC), 2 * DEC, cw // (2 * DEC), 2 * DEC).max(axis=(1, 3))
    lo = g[:hh, :ww].reshape(hh // DEC, DEC, ww // DEC, DEC).mean(axis=(1, 3))
    return det.astype(np.float32), cl.astype(np.float32), lo.astype(np.float32)


def main() -> int:
    paths = sorted(
        os.path.join(L.STACK, f) for f in os.listdir(L.STACK) if f.lower().endswith(".arw")
    )
    n = len(paths)
    t0 = time.time()
    dmax = None
    clip = None
    lmin = None
    lmax = None
    with ProcessPoolExecutor(max_workers=8) as ex:
        for i, (det, cl, lo) in enumerate(ex.map(_one, paths, chunksize=4)):
            if dmax is None:
                dmax, clip, lmin, lmax = det, cl, lo.copy(), lo.copy()
            else:
                np.maximum(dmax, det, out=dmax)
                np.maximum(clip, cl, out=clip)
                np.minimum(lmin, lo, out=lmin)
                np.maximum(lmax, lo, out=lmax)
            if (i + 1) % 75 == 0:
                print(f"  {i+1:3d}/{n}  {time.time()-t0:6.1f}s", flush=True)
    print(f"full-stack max-detail map: {dmax.shape}  {time.time()-t0:.1f}s")

    drift = json.load(open(os.path.join(OUTDIR, "s1_drift.json"), encoding="utf-8"))
    a_re = np.array(drift["a_re"])
    a_im = np.array(drift["a_im"])
    b_re = np.array(drift["b_re"])
    b_im = np.array(drift["b_im"])

    def drift_per_step(cx, cy):
        z = complex(cx, cy)
        w = (a_re + 1j * a_im) * z + (b_re + 1j * b_im)
        return float(np.median(np.abs(np.diff(w))))

    H, W = dmax.shape
    ph, pw = H * DEC, W * DEC
    cands = []
    for y in range(BORDER, ph - WIN - BORDER + 1, STRIDE):
        for x in range(BORDER, pw - WIN - BORDER + 1, STRIDE):
            ys, xs = y // DEC, x // DEC
            ye, xe = (y + WIN) // DEC, (x + WIN) // DEC
            if clip[ys:ye, xs:xe].max() > 0:
                continue
            cands.append(
                dict(
                    x=x,
                    y=y,
                    peak_detail=float(dmax[ys:ye, xs:xe].mean()),
                    lo_min=float(lmin[ys:ye, xs:xe].mean()),
                    lo_max=float(lmax[ys:ye, xs:xe].mean()),
                    drift=drift_per_step(x + WIN / 2, y + WIN / 2),
                )
            )
    print(f"windows        : {len(cands)} unclipped candidates")

    cands.sort(key=lambda c: c["peak_detail"])
    print("\nflattest 6 by max-over-299 detail:")
    for c in cands[:6]:
        print(
            f"  ({c['x']:5d},{c['y']:5d})  peak-detail {c['peak_detail']:10.1f}  "
            f"signal {c['lo_min']:7.1f}..{c['lo_max']:7.1f} DN  drift/step {c['drift']:5.3f} px"
        )
    print("\nsharpest 6 by max-over-299 detail:")
    for c in cands[::-1][:6]:
        print(
            f"  ({c['x']:5d},{c['y']:5d})  peak-detail {c['peak_detail']:10.1f}  "
            f"signal {c['lo_min']:7.1f}..{c['lo_max']:7.1f} DN  drift/step {c['drift']:5.3f} px"
        )

    # Detail ROIs: top quartile by peak detail, then spread as far as the
    # geometry allows on measured drift/step.
    thr = np.percentile([c["peak_detail"] for c in cands], 75)
    det = [c for c in cands if c["peak_detail"] >= thr]
    det.sort(key=lambda c: c["drift"])
    chosen = {
        "ROI-LOWDRIFT": det[0],
        "ROI-MIDDRIFT": det[len(det) // 2],
        "ROI-HIGHDRIFT": det[-1],
        "ROI-FLAT": cands[0],
    }
    print(f"\ndetail pool    : {len(det)} windows at/above the 75th pct of peak detail")
    print(f"drift span     : {det[0]['drift']:.3f} .. {det[-1]['drift']:.3f} px/step")
    print()
    for nm, c in chosen.items():
        print(
            f"{nm:<14} ({c['x']:5d},{c['y']:5d})  peak-detail {c['peak_detail']:10.1f}  "
            f"drift/step {c['drift']:5.3f} px  signal {c['lo_min']:7.1f}..{c['lo_max']:7.1f} DN"
        )

    dst = os.path.join(OUTDIR, "s2b_rois.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(
            {"chosen": chosen, "n_cands": len(cands), "detail_thr": float(thr), "cands": cands},
            f,
            indent=2,
        )
    np.save(os.path.join(L.OUT, "m93_maxdetail.npy"), dmax)
    print(f"\nwrote          : {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
