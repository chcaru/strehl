"""Known-answer commissioning of the held-out instrument.

A band-limited random scene (sinusoids up to --fmax cycles/sensor px, per
channel with correlated luma) is sampled at each synthetic frame's CFA sites,
with frame placements that shift the ROI by a chosen sub-pixel phase per frame.
Expected: with phase diversity, B < A on held-out error and Bp loses B's gain;
with zero diversity (--spread 0), B ~ Bp and no gain over A is claimed.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import BLACK, GAIN_DN_PER_E, READ_E, cfa_channel, frame_to_ref
import holdout as H

ap = argparse.ArgumentParser()
ap.add_argument("--spread", type=float, default=1.5, help="total phase spread across frames, sensor px")
ap.add_argument("--fmax", type=float, default=0.6)
ap.add_argument("--frames", type=int, default=7)
ap.add_argument("--chroma-falloff", type=float, default=3.0)
ap.add_argument("--optics", type=float, default=0.0, help="effective f-number for a diffraction MTF (0 = none)")
ap.add_argument("--defocus", type=float, default=0.0, help="blur sigma (sensor px) of the window's edge frames")
ap.add_argument("--reg-noise", type=float, default=0.0, help="registration error sigma, sensor px")
ap.add_argument("--c", action="append", default=[], help="lam_luma,lam_chroma,lam_stay")
ap.add_argument("--signal", type=float, default=3000)
args = ap.parse_args()
rng = np.random.default_rng(1)
gw, gh = 3516, 2344
centre = complex(gw / 2, gh / 2)
roi = (1000, 1000, 96)
# scene: luma sinusoids shared, chroma lower amplitude
K = 300
fr = rng.uniform(0.02, args.fmax, K)
th = rng.uniform(0, np.pi, K)
ph = rng.uniform(0, 2 * np.pi, K)
amp = rng.normal(0, 1, K) / np.sqrt(K) * (1 / (1 + 3 * fr))
camp = rng.normal(0, 0.3, (3, K)) / np.sqrt(K) * (1 / (1 + args.chroma_falloff * fr))
if args.optics > 0:
    fc = 1 / (0.55e-3 * args.optics) * 5.12e-3  # cycles per sensor px at 5.12 um pitch
    nu = np.minimum(fr / fc, 1)
    mtf = (2 / np.pi) * (np.arccos(nu) - nu * np.sqrt(1 - nu * nu)) * np.abs(np.sinc(fr))
    amp, camp = amp * mtf, camp * mtf
BLUR = np.ones(K)


def scene(ch, x, y, blur=None):
    blur = np.ones(K) if blur is None else blur
    arg = 2 * np.pi * fr[None] * (np.cos(th)[None] * x[:, None] + np.sin(th)[None] * y[:, None]) + ph[None]
    s = np.cos(arg)
    return args.signal * (1 + 0.5 * (s @ (amp * blur) + s @ (camp[ch] * blur)))


frames = []
for k in range(args.frames):
    # radial-ish: translate along a fixed direction plus a small orthogonal jitter
    d = args.spread * (k / max(args.frames - 1, 1) - 0.5)
    b = complex(d / 2 * 0.8, d / 2 * 0.6 + rng.normal(0, 0.02))
    t = (complex(1, 0), b)
    edge = abs(k / max(args.frames - 1, 1) - 0.5) * 2
    sig = args.defocus * edge
    blur = np.exp(-2 * np.pi ** 2 * sig ** 2 * fr ** 2)
    true_t = (t[0], t[1] + complex(*rng.normal(0, args.reg_noise / 2, 2)))
    box = H.frame_box(t, roi, centre, 24)
    bx0, by0, bx1, by1 = box
    yy, xx = np.mgrid[by0:by1, bx0:bx1]
    rx, ry = frame_to_ref(true_t, xx.ravel().astype(float), yy.ravel().astype(float), centre)
    c = cfa_channel(xx.ravel(), yy.ravel())
    v = np.zeros(len(c))
    for ch in range(3):
        m = c == ch
        v[m] = scene(ch, rx[m], ry[m], blur)
    noise = rng.normal(0, np.sqrt(GAIN_DN_PER_E * v + (GAIN_DN_PER_E * READ_E) ** 2))
    patch = np.clip(np.round(v + noise + BLACK), 0, 65535).astype(np.uint16).reshape(yy.shape)
    frames.append((patch, (bx0, by0), t, np.ones(3), 1.0))
x0, y0, s = roi
grid = (x0 - 6, y0 - 6, s + 12, s + 12)
inner = (x0 + 8, y0 + 8, s - 16)
tot = {}
for h in range(len(frames)):
    train = [f for k, f in enumerate(frames) if k != h]
    imgs = {"A": H.arm_a(train, grid, False, centre), "B": H.arm_b(train, grid, False, centre, 0.02),
            "Bp": H.arm_b(train, grid, False, centre, 0.02, snap=True)}
    for spec in args.c:
        ll, lc, ls = map(float, spec.split(","))
        imgs[f"C{spec}"] = H.arm_c(train, grid, False, centre, imgs["A"], lam_luma=ll, lam_chroma=lc, lam_stay=ls)
    # truth error on the grid as well
    yy, xx = np.mgrid[grid[1]:grid[1] + grid[3], grid[0]:grid[0] + grid[2]].astype(float)
    sl = (slice(14, -14), slice(14, -14))
    for n, img in imgs.items():
        sc = H.score(H.predict_holdout(img, frames[h], grid, False, centre, inner))
        truth = np.mean([np.mean((img[ch][sl] - scene(ch, xx[sl].ravel(), yy[sl].ravel()).reshape(xx[sl].shape)) ** 2)
                         for ch in range(3)])
        e = tot.setdefault(n, [0, 0, 0])
        e[0] += np.mean([sc[c]["mse"] / sc[c]["noise"] for c in "rgb"])
        e[1] += np.mean([sc[c]["mse_fitted"] / sc[c]["noise"] for c in "rgb"])
        e[2] += truth
for n, e in tot.items():
    print(f"spread {args.spread} {n}: holdout mse/noise {e[0] / len(frames):.3f} fitted {e[1] / len(frames):.3f} "
          f"truth mse {e[2] / len(frames):.1f}")
