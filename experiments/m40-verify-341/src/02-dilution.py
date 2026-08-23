"""M40 verification, script 02 -- is script 01's null DILUTED, and what survives if not?

Script 01 found the gate-0 per-pixel selection inflation at 1.012-1.019 (pixel domain)
and 1.012-1.019 (gradient domain) against a shift control, where the shipped constant is
1.074.  One objection could rescue the constant: the winner map is 17x17-regularised and
has only 4-8 distinct winners in a 256x256 ROI, so a SHIFTED or PERMUTED winner map may
re-elect the SAME frame at most pixels.  A null that agrees with the treatment at most
pixels is diluted toward 1 and would understate the excess.

So this script removes the dilution three ways, and adds a completely dilution-free
estimator:

  D1  report the winner histogram, its concentration sum(p_k^2), and the fraction of
      pixels at which each null arm actually re-elects a different frame.
  D2  a much larger shift, (128,128), and the conditional estimator restricted to the
      pixels where the shifted winner DIFFERS from the true one.
  E5  the exhaustive null.  For every pixel, average the squared deviation over ALL N
      frames:  null_i = (1/N) * sum_k (x_k[i] - mu[i])^2.  This is exactly "what a frame
      chosen without reference to this pixel's noise would have cost", it uses every
      frame so it cannot be diluted, and it needs no noise model at all.
          E5 = sqrt( mean_i(d_true^2) / mean_i(null_i) )
      Gradient-domain twin E5g uses mean over k of grad_energy(x_k - mu).

The per-frame profile of mean((x_k - mu)^2) is printed too, because E5 assumes the
frames are exchangeable and photometric drift or focus breathing would break that.

PRE-REGISTERED (rule 20).  The constant survives if the dilution-corrected estimators
land near 1.074.  It does not survive if they stay near 1.02.  D1 tells us which reading
script 01's numbers deserve: if the null arms re-elect a different frame at >60% of
pixels there was never much dilution to correct.

Outputs: out/02-dilution.txt, out/02-dilution.json
"""

import glob
import json
import os
import sys
import time

import numpy as np
import rawpy

BLACK = 512.0
GAIN_DIV = 436.8
RN_E_LOW = 4.20
SIGMA_EPS = 1e-3
WINDOW_RADIUS, REG_RADIUS, MARGIN = 13, 8, 24

STACKS = {
    "109MSDCF": dict(
        path=r"C:\dev\macro\test\109MSDCF",
        iso=160.0,
        rois={
            "flat-M2 2272,1344": (2272, 1344, 256, 256),
            "flat-M11 2352,1408": (2352, 1408, 256, 256),
        },
    ),
    "119MSDCF": dict(
        path=r"C:\dev\macro\test\119MSDCF",
        iso=50.0,
        rois={
            "flat-M11 2896,1968": (2896, 1968, 256, 256),
            "flat-M11 3056,416": (3056, 416, 256, 256),
        },
    ),
}


def sigma_luma(S, g, read_dn):
    return np.sqrt(0.5 * (g * np.maximum(S, 0.0) + read_dn * read_dn))


def box_mean(a, r):
    H, W = a.shape
    c = np.pad(np.cumsum(np.cumsum(a, 0), 1), ((1, 0), (1, 0)))
    y0 = np.maximum(np.arange(H) - r, 0)
    y1 = np.minimum(np.arange(H) + r, H - 1)
    x0 = np.maximum(np.arange(W) - r, 0)
    x1 = np.minimum(np.arange(W) + r, W - 1)
    s = (
        c[np.ix_(y1 + 1, x1 + 1)]
        - c[np.ix_(y0, x1 + 1)]
        - c[np.ix_(y1 + 1, x0)]
        + c[np.ix_(y0, x0)]
    )
    return s / np.outer(y1 - y0 + 1, x1 - x0 + 1)


def sobel_mag(a):
    p = np.pad(a, 1, mode="edge")
    gx = (
        p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]
        - p[:-2, :-2] - 2 * p[1:-1, :-2] - p[2:, :-2]
    ) * 0.125
    gy = (
        p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]
        - p[:-2, :-2] - 2 * p[:-2, 1:-1] - p[:-2, 2:]
    ) * 0.125
    return np.hypot(gx, gy)


def grad_energy(v):
    dx = v[:-1, 1:] - v[:-1, :-1]
    dy = v[1:, :-1] - v[:-1, :-1]
    return float((dx * dx + dy * dy).mean())


def load_stack(path, iso, rois):
    frames = sorted(glob.glob(os.path.join(path, "*.ARW")))
    assert frames, path
    g = iso / GAIN_DIV
    read_dn = RN_E_LOW * g
    acc = {k: dict(L=[], reg=[]) for k in rois}
    t0 = time.time()
    for fi, p in enumerate(frames):
        r = rawpy.imread(p)
        a = r.raw_image_visible
        for k, (x, y, w, h) in rois.items():
            cx, cy, cw, ch = x - MARGIN, y - MARGIN, w + 2 * MARGIN, h + 2 * MARGIN
            sub = a[2 * cy : 2 * (cy + ch), 2 * cx : 2 * (cx + cw)].astype(np.float64)
            g1 = sub[0::2, 1::2]
            g2 = sub[1::2, 0::2]
            luma_f = 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))
            focus = box_mean(sobel_mag(luma_f), WINDOW_RADIUS) / np.maximum(
                sigma_luma(luma_f, g, read_dn), SIGMA_EPS
            )
            acc[k]["reg"].append(box_mean(focus, REG_RADIUS).astype(np.float32))
            acc[k]["L"].append(0.5 * (g1 + g2) - BLACK)
        del r, a
    print(f"    decoded {len(frames)} frames in {time.time() - t0:.1f}s", flush=True)
    return frames, g, read_dn, acc


def main():
    out = open("out/02-dilution.txt", "w", encoding="utf-8")

    def emit(s=""):
        print(s, flush=True)
        out.write(s + "\n")

    emit("=" * 100)
    emit("M40 script 02 -- dilution of the gate-0 null, and the exhaustive-null estimator E5")
    emit("=" * 100)
    emit("")
    results = {}
    for stack, cfg in STACKS.items():
        emit(f"### stack {stack}   iso {cfg['iso']:.0f}")
        frames, g, read_dn, acc = load_stack(cfg["path"], cfg["iso"], cfg["rois"])
        N = len(frames)
        rng = np.random.default_rng(4041)
        sl = (slice(MARGIN, MARGIN + 256), slice(MARGIN, MARGIN + 256))
        for k, (x, y, w, h) in cfg["rois"].items():
            L = np.stack(acc[k]["L"])[:, sl[0], sl[1]]
            R = np.stack(acc[k]["reg"])[:, sl[0], sl[1]]
            win = R.argmax(axis=0)
            mu = L.mean(axis=0)
            yy, xx = np.mgrid[0:h, 0:w]

            counts = np.bincount(win.ravel(), minlength=N)
            p = counts / counts.sum()
            conc = float((p * p).sum())

            arms = {
                "shift37": np.roll(win, (37, 53), axis=(0, 1)),
                "shift128": np.roll(win, (128, 128), axis=(0, 1)),
                "shuffle": rng.permutation(win.ravel()).reshape(win.shape),
            }

            d_true = L[win, yy, xx] - mu
            dev = L - mu[None, :, :]
            null_pix = (dev * dev).mean(axis=0)  # (1/N) sum_k (x_k - mu)^2, per pixel
            per_frame = [float((dev[j] * dev[j]).mean()) for j in range(N)]
            null_grad = float(np.mean([grad_energy(dev[j]) for j in range(N)]))

            e5 = float(np.sqrt((d_true * d_true).mean() / null_pix.mean()))
            e5g = float(np.sqrt(grad_energy(d_true) / null_grad))

            emit(f"  --- ROI {k} ---")
            top = np.argsort(-counts)[:5]
            emit(
                "    winner histogram (top 5): "
                + ", ".join(f"f{int(t)}={100 * p[t]:.1f}%" for t in top if counts[t])
            )
            emit(
                f"    concentration sum(p^2) = {conc:.4f}  -> a histogram-preserving null "
                f"re-elects the same frame at ~{100 * conc:.1f}% of pixels by chance alone"
            )
            row = dict(N=N, concentration=conc, E5=e5, E5g=e5g, arms={})
            emit(
                "      null arm     changed%   E2 all px   E2 changed-px only   E4 all px   "
                "E4 changed-px only"
            )
            for name, wmap in arms.items():
                d_n = L[wmap, yy, xx] - mu
                changed = wmap != win
                frac = float(changed.mean())
                e2_all = float(np.sqrt((d_true**2).mean() / (d_n**2).mean()))
                if changed.sum() > 100:
                    e2_ch = float(
                        np.sqrt((d_true[changed] ** 2).mean() / (d_n[changed] ** 2).mean())
                    )
                else:
                    e2_ch = float("nan")
                e4_all = float(np.sqrt(grad_energy(d_true) / grad_energy(d_n)))
                # gradient domain on a subset is not defined pointwise, so mask by
                # zeroing the unchanged pixels in BOTH arms and comparing like with like
                m = changed.astype(np.float64)
                e4_ch = float(np.sqrt(grad_energy(d_true * m) / grad_energy(d_n * m)))
                row["arms"][name] = dict(
                    changed=frac, E2_all=e2_all, E2_changed=e2_ch, E4_all=e4_all, E4_changed=e4_ch
                )
                emit(
                    f"      {name:10s}  {100 * frac:7.2f}%   {e2_all:9.4f}x   {e2_ch:18.4f}x   "
                    f"{e4_all:9.4f}x   {e4_ch:17.4f}x"
                )
            emit(
                f"    E5  exhaustive null, pixel domain   = {e5:.4f}x     "
                f"[SELECTION_INFLATION is 1.0740x]"
            )
            emit(f"    E5g exhaustive null, gradient domain = {e5g:.4f}x")
            emit(
                "    per-frame mean((x_k - mu)^2), DN^2: "
                + " ".join(f"{v:.0f}" for v in per_frame)
            )
            emit(
                f"      -> spread across frames {min(per_frame):.0f}..{max(per_frame):.0f}, "
                f"true-winner arm {float((d_true**2).mean()):.0f}"
            )
            emit("")
            results[f"{stack} | {k}"] = row
        del acc
        emit("")

    json.dump(results, open("out/02-dilution.json", "w"), indent=1)
    emit("=" * 100)
    emit("SUMMARY")
    emit("=" * 100)
    emit(f"  {'ROI':34s} {'conc':>7s} {'E5 pix':>9s} {'E5 grad':>9s} {'E2 chg-px':>10s}")
    for name, r in results.items():
        emit(
            f"  {name:34s} {r['concentration']:7.3f} {r['E5']:8.4f}x {r['E5g']:8.4f}x "
            f"{r['arms']['shift128']['E2_changed']:9.4f}x"
        )
    out.close()


if __name__ == "__main__":
    sys.exit(main())
