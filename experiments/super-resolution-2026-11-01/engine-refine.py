"""Arm D: refine the actual engine output from original CFA samples, each frame
weighted by its own local sharpness, with the joint chroma-smooth correction.

Per ROI: frames within +-half_window of the ROI's focus peak; per frame a local
focus map (Gaussian-pooled squared Laplacian of its pulled MHC green on the
reference grid); weight = (F_k / max_k F)^p, zero below --floor. The engine
master is mapped to camera RGB by a 3x3+offset fit against the plain average
(colour only). D = engine + correction. Also reports, as a placebo, D built
with sub-pixel phase destroyed (samples snapped to the reference lattice).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, laplace

sys.path.insert(0, str(Path(__file__).parent))
from common import BLACK, cfa_channel, channel_transform, cr_sample, decode_many, load_alignment, mhc, ref_to_frame
import holdout as H

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alignment", required=True)
    ap.add_argument("--master", required=True)
    ap.add_argument("--crop", default="76,52", help="master pixel = sensor - crop")
    ap.add_argument("--pass-range", required=True)
    ap.add_argument("--roi", action="append", required=True)
    ap.add_argument("--engine-dump", help="lighting dump group .f32 (R,G1,G2,B planes) to use instead of the master")
    ap.add_argument("--dump-size", default="3440,2292")
    ap.add_argument("--half-window", type=int, default=10)
    ap.add_argument("--power", type=float, default=4)
    ap.add_argument("--floor", type=float, default=0.25)
    ap.add_argument("--ca", type=int, default=1)
    ap.add_argument("--c", type=float, nargs=3, default=[0.02, 0.5, 0.001])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    place, paths, (gw, gh) = load_alignment(args.alignment)
    centre = complex(gw / 2, gh / 2)
    first, last = map(int, args.pass_range.split(","))
    cdx, cdy = (0, 0) if args.crop == "auto" else map(int, args.crop.split(","))
    rois = [tuple(map(int, r.split(","))) for r in args.roi]
    idx = [i for i in range(first, last + 1) if place[i] is not None]
    jobs = [(paths[i], [H.frame_box(place[i], roi, centre, 24) for roi in rois]) for i in idx]
    dec = decode_many(jobs)
    if args.engine_dump:
        dw, dh = map(int, args.dump_size.split(","))
        planes = np.fromfile(args.engine_dump, dtype="<f4").reshape(4, dh, dw)
        mos = np.zeros((2 * dh, 2 * dw), np.float32)
        mos[0::2, 0::2], mos[0::2, 1::2], mos[1::2, 0::2], mos[1::2, 1::2] = planes
        wbd = dec[0][1]  # camera WB (R, G, B) / G, as the engine develops
        mos[0::2, 0::2] *= wbd[0]
        mos[1::2, 1::2] *= wbd[2]
        master = mhc(mos, 0, 0).transpose(1, 2, 0)
        del planes, mos
    else:
        master = tifffile.imread(args.master)
    use_ca = bool(args.ca)
    for r, roi in enumerate(rois):
        x0, y0, s = roi
        allf = [(dec[k][0][r], tuple(jobs[k][1][r][:2]), place[i], dec[k][1], 1.0) for k, i in enumerate(idx)]
        scores = np.array([H.focus_score(f[0]) for f in allf])
        pk = int(np.argmax(scores))
        win = range(max(0, pk - args.half_window), min(len(allf), pk + args.half_window + 1))
        g_ref = np.mean(allf[pk][0][0::2, 1::2].astype(float) - BLACK)
        frames = []
        for k in win:
            p, o, t, wb, _ = allf[k]
            frames.append((p, o, t, wb, g_ref / np.mean(p[0::2, 1::2].astype(float) - BLACK)))
        grid = (x0 - 6, y0 - 6, s + 12, s + 12)
        gx0, gy0, gwd, ghd = grid
        yy, xx = np.mgrid[gy0:gy0 + ghd, gx0:gx0 + gwd].astype(float)
        pulled = []
        for p, (bx0, by0), t, wb, gain in frames:
            h, w = p.shape
            yi, xi = np.mgrid[by0:by0 + h, bx0:bx0 + w]
            rgb = mhc((p.astype(float) - BLACK) * wb[cfa_channel(xi, yi)] * gain, bx0, by0)
            out = []
            for ch in range(3):
                fx, fy = ref_to_frame(channel_transform(t, "rgb"[ch], use_ca), xx, yy, centre)
                out.append(np.nan_to_num(cr_sample(rgb[ch], fx - bx0, fy - by0)))
            pulled.append(np.stack(out))
        pulled = np.stack(pulled)
        F = np.stack([gaussian_filter(laplace(gaussian_filter(q[1], 0.7)) ** 2, 3) for q in pulled])
        rel = F / F.max(0, keepdims=True)
        W = np.where(rel >= args.floor, rel ** args.power, 0.0)
        avg = pulled.mean(0)
        fused = (pulled * W[:, None]).sum(0) / W.sum(0)[None]
        if args.crop == "auto" and r == 0:
            # locate the ROI in the master by NCC of green against the fused estimate
            from scipy.signal import fftconvolve
            t = fused[1] - fused[1].mean()
            R = 200
            S = master[max(gy0 - R, 0):gy0 + ghd + R, max(gx0 - R, 0):gx0 + gwd + R, 1].astype(float)
            num = fftconvolve(S, t[::-1, ::-1], mode="valid")
            ones = np.ones_like(t)
            s1 = fftconvolve(S, ones, mode="valid")
            s2 = fftconvolve(S * S, ones, mode="valid")
            sd = np.sqrt(np.maximum(s2 - s1 * s1 / t.size, 1e-9))
            ncc = num / sd / np.sqrt((t * t).sum())
            iy, ix = np.unravel_index(np.argmax(ncc), ncc.shape)
            cdx = gx0 - (max(gx0 - R, 0) + ix)
            cdy = gy0 - (max(gy0 - R, 0) + iy)
            print(f"  master offset ({cdx},{cdy}) ncc {ncc.max():.3f}", flush=True)
        m = master[gy0 - cdy:gy0 - cdy + ghd, gx0 - cdx:gx0 - cdx + gwd].astype(float).transpose(2, 0, 1)
        X = np.concatenate([m.reshape(3, -1), np.ones((1, m[0].size))]).T
        coef, *_ = np.linalg.lstsq(X, fused.reshape(3, -1).T, rcond=None)  # colour map onto the sharp fusion
        eng = (X @ coef).T.reshape(3, ghd, gwd)
        D = H.arm_c(frames, grid, use_ca, centre, eng, *args.c, weights=list(W))
        Df = H.arm_c(frames, grid, use_ca, centre, fused, *args.c, weights=list(W))
        print(f"roi {roi}: window {idx[win[0]]}..{idx[win[-1]]}, peak {idx[pk]}", flush=True)
        for name, a in [("engine", eng), ("fused", fused), ("D", D), ("Dfused", Df)]:
            hb = a[:, 8:-8, 8:-8] - np.stack([gaussian_filter(c, 1.5) for c in a[:, 8:-8, 8:-8]])
            print(f"  {name:>7}: high-band rms r/g/b " + " ".join(f"{np.sqrt(np.mean(c ** 2)):7.2f}" for c in hb))
        np.save(f"{args.out}-roi{r}.npy", np.stack([eng, D, fused, Df]))


if __name__ == "__main__":
    main()
