#!/usr/bin/env python3
"""STAGE A -- the frame-side oracle.

For every tile of a subject, walk the WHOLE bracket and record the per-band
band power.  Then report, per tile, the through-focus contrast: how much more
band power the best-focused frame carries than the out-of-focus frames do.

This stage never touches the merge.  Every number is a comparison of frames
against other frames, all decoded by one identical path, so the sensor noise is
common-mode and cancels without being estimated (see ora.through_focus_contrast).

It answers, on its own, the half of the decisive question that matters most:
where the merged master is smooth blur, IS THERE A SOURCE FRAME WITH STRUCTURE
THERE AT ALL?  If not, the bracket never covered it and the merge cannot be
blamed.

Writes a .npz to D:\\strehl-out\\V-ORACLE\\stageA\\<subject>.npz.

Usage:  python stageA.py <subject> [--every N] [--tile PX]
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--every", type=int, default=1,
                    help="frame stride; 1 = every frame in the bracket")
    ap.add_argument("--tile", type=int, default=128)
    ap.add_argument("--maxframes", type=int, default=0,
                    help="if >0, sample this many frames evenly instead")
    args = ap.parse_args()

    fs = ora.frames_of(args.subject)
    n = len(fs)
    if args.maxframes and n > args.maxframes:
        ks = np.unique(np.linspace(0, n - 1, args.maxframes).round().astype(int))
    else:
        ks = np.arange(0, n, args.every)
    print(f"{args.subject}: {n} frames, using {len(ks)} "
          f"({'all' if len(ks) == n else 'sampled'})  tile={args.tile}px green")

    var_k, lev_k, cov_k = [], [], []
    t0 = time.time()
    for i, k in enumerate(ks):
        g1, g2 = ora.green_pair(fs[k])
        st = ora.tile_stats(g1, g2, args.tile)
        var_k.append(st["var"].astype(np.float32))
        cov_k.append(st["cov"].astype(np.float32))
        lev_k.append(st["level"].astype(np.float32))
        if i % 20 == 0 or i == len(ks) - 1:
            el = time.time() - t0
            print(f"  {i + 1}/{len(ks)}  {el:6.1f}s  "
                  f"eta {el / (i + 1) * (len(ks) - i - 1):6.1f}s", flush=True)
    var_k = np.stack(var_k)
    cov_k = np.stack(cov_k)
    lev_k = np.stack(lev_k)
    nr, nc = st["nr"], st["nc"]

    # Per-stack gain, for the level-drift correction only.  Estimated from the
    # coarse-band identity  Var - Cov = noise power  (exact where the G1/G2
    # half-pixel offset is negligible, which commission.py C5 measured at
    # recovery 0.95 for band 3), pooled over every tile and frame.  Only the
    # DIFFERENTIAL level correction uses it, so its accuracy is second order.
    kap = ora.kappa()
    npow = np.maximum(var_k[:, 3] - cov_k[:, 3], 0.0) / kap[3]
    lo = np.quantile(npow, 0.25)
    hi = np.quantile(npow, 0.75)
    m = (npow >= lo) & (npow <= hi)
    g_est = float(np.median(lev_k[m] / np.maximum(npow[m], 1e-6)))
    print(f"  per-stack gain for the drift correction: g = {g_est:.3f} "
          f"DN/DN^2  (level {lev_k.mean():.0f} DN -> sigma "
          f"{np.sqrt(lev_k.mean() / g_est):.2f} DN)")

    tf = ora.through_focus_contrast(var_k, lev_k, g_est)
    tf_nc = ora.through_focus_contrast(var_k, lev_k, g_est, level_correct=False)

    out = os.path.join(ora.OUT, "stageA")
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, args.subject + ".npz")
    np.savez_compressed(
        p, subject=args.subject, frames=np.array(ks), nframes=n,
        tile=args.tile, nr=nr, nc=nc, g_est=g_est,
        contrast=tf["contrast"], hi=tf["hi"], lo=tf["lo"], best_k=tf["best_k"],
        contrast_nolevelcorr=tf_nc["contrast"],
        level_med=np.median(lev_k, axis=0),
        level_spread=(lev_k.max(axis=0) - lev_k.min(axis=0)),
        var_lo=np.quantile(var_k, 0.25, axis=0).astype(np.float32),
        cov_hi=cov_k.max(axis=0).astype(np.float32),
        # The full (K, NBAND, nr, nc) cube.  It is only a few MB and without it
        # no question of the form "which frame should have won, and which one
        # did" can be answered afterwards without decoding the bracket again.
        var_k=var_k, lev_k=lev_k, cov_k=cov_k,
    )
    print(f"  wrote {p}")

    for b in range(ora.NBAND):
        c = tf["contrast"][b]
        cn = tf_nc["contrast"][b]
        print(f"  band {b}: contrast median={np.median(c):10.3f} "
              f"p90={np.quantile(c, 0.9):10.3f} max={c.max():10.3f}   "
              f"level-correction moved the median by "
              f"{100 * (np.median(c) - np.median(cn)) / max(abs(np.median(cn)), 1e-9):+6.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
