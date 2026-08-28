"""V-KILLB0 ground2.py -- ground truth, with the two defects of ground.py fixed.

ground.py returned rho ~= 0.19 for BOTH arms and marginally favoured b0x4, and
its K1 focus control failed the bar I set.  Two reasons, both fixable:

 1. TONE.  Masters are sRGB-encoded, develops are linear.  leaf-2 is dark
    (auto-exposure wanted +3.19 stops), so the sRGB curve is violently
    nonlinear exactly where this subject lives.  FIX: apply the exact inverse
    sRGB OETF to the masters so every image compared is linear.
 2. REFERENCE NOISE.  A single develop of a dark subject is noise-dominated, and
    rho with a noisy reference is capped by the reference's own SNR, which
    flatters whichever arm is smoother regardless of who is right.  FIX: average
    the 5 develops nearest the focus peak.  Adjacent frames in a focus stack
    differ little in focus at a given tile, so this cuts reference noise by
    ~sqrt(5) while keeping the structure.

CONTROLS:
  K0  rho(ref, ref) == 1.000000
  K1  in-focus rho must clearly exceed rho against a DEFOCUSED frame
  K2  the 5-frame average must not have destroyed the focus: its band amplitude
      must stay within 30% of the single peak frame's.  If averaging blurred the
      reference, the reference is not ground truth and the test is void.
Each arm is scored at its OWN best integer shift, which cannot favour either.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-HEADTOHEAD2")
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-LINEAR2")
import h2                                    # noqa: E402
import bandsignal as BS                      # noqa: E402

T, MARGIN, NY, NX = BS.T, BS.MARGIN, 10, 13
DEV = r"C:\dev\strehl-out\V-NOISE2\leaf\lintiff"
OUT = r"C:\dev\strehl-out\V-KILLB0"
KEY = "leaf-2-cpl"
F0, F1 = 0.05, 0.14
WIN, SEARCH = 512, 48


def srgb_to_linear(u16):
    v = u16.astype(np.float64) / 65535.0
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def radial(img, f0, f1):
    a = np.fft.rfft2(img.astype(np.float64))
    h, w = img.shape
    r = np.hypot(np.fft.fftfreq(h)[:, None], np.fft.rfftfreq(w)[None, :])
    a *= ((r >= f0) & (r < f1))
    return np.fft.irfft2(a, s=img.shape)


def best(ref, arm):
    c = WIN // 2
    r = ref[c - T // 2:c + T // 2, c - T // 2:c + T // 2]
    r = r - r.mean(); er = np.sqrt((r * r).mean())
    bb, bsh = -2.0, (0, 0)
    for dy in range(-SEARCH, SEARCH + 1, 2):
        for dx in range(-SEARCH, SEARCH + 1, 2):
            a = arm[c + dy - T // 2:c + dy + T // 2, c + dx - T // 2:c + dx + T // 2]
            a = a - a.mean(); ea = np.sqrt((a * a).mean())
            if ea == 0:
                continue
            v = (r * a).mean() / (er * ea)
            if v > bb:
                bb, bsh = v, (dy, dx)
    return bb, bsh


def stretch(a):
    lo, hi = np.percentile(a, 0.5), np.percentile(a, 99.5)
    return np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)


files = sorted(f for f in os.listdir(DEV) if f.lower().endswith(".tif"))
step = max(1, round(len(files) / 80))
selp = np.load(os.path.join(OUT, f"{KEY}-selp.npy"))
mm = tifffile.memmap(os.path.join(DEV, files[0]), mode="r")
H, W = mm.shape[0], mm.shape[1]; del mm
ys = np.linspace(MARGIN, H - MARGIN - T, NY).astype(int)
xs = np.linspace(MARGIN, W - MARGIN - T, NX).astype(int)
pos = [(int(y), int(x)) for y in ys for x in xs]

print(f"== GROUND TRUTH v2 {KEY}   band {F0}-{F1} cyc/px   ALL IMAGES LINEAR")
ma = srgb_to_linear(tifffile.imread(os.path.join(OUT, "default", KEY + ".tiff"))[..., :3])
mb = srgb_to_linear(tifffile.imread(os.path.join(OUT, "b0x4", KEY + ".tiff"))[..., :3])
ma = h2.luma709(ma); mb = h2.luma709(mb)

order = np.argsort(-np.nanmax(selp, axis=0))
print(f"   {'tile':>5} {'frame':>6} {'K2 amp':>7} | {'rho DEFAULT':>12} {'rho b0x4':>9} "
      f"| {'winner':>8}  {'amp d':>7} {'amp b':>7}")
rows = []
for t in order[:8]:
    y, x = pos[t]
    fi = int(np.nanargmax(selp[:, t]) * step)
    lo = int(np.nanargmin(selp[:, t]) * step)
    cy, cx = y + T // 2, x + T // 2
    sy, sx = slice(cy - WIN // 2, cy + WIN // 2), slice(cx - WIN // 2, cx + WIN // 2)
    idxs = [i for i in (fi - 2 * step, fi - step, fi, fi + step, fi + 2 * step)
            if 0 <= i < len(files)]
    acc = None
    for i in idxs:
        c = h2.luma709(np.asarray(tifffile.memmap(os.path.join(DEV, files[i]), mode="r")[sy, sx, :3], np.float64))
        acc = c if acc is None else acc + c
    ref = radial(acc / len(idxs), F0, F1)
    one = radial(h2.luma709(np.asarray(tifffile.memmap(os.path.join(DEV, files[fi]), mode="r")[sy, sx, :3], np.float64)), F0, F1)
    k2 = ref.std() / one.std()
    dfc = radial(h2.luma709(np.asarray(tifffile.memmap(os.path.join(DEV, files[lo]), mode="r")[sy, sx, :3], np.float64)), F0, F1)
    A, B = radial(ma[sy, sx], F0, F1), radial(mb[sy, sx], F0, F1)
    k0 = best(ref, ref)[0]
    if abs(k0 - 1.0) > 1e-6:
        raise SystemExit(f"K0 FAILED {k0}")
    ra, sha = best(ref, A); rb, shb = best(ref, B); rk, _ = best(dfc, A)
    c = WIN // 2
    aa = A[c + sha[0] - T//2:c + sha[0] + T//2, c + sha[1] - T//2:c + sha[1] + T//2].std()
    bb_ = B[c + shb[0] - T//2:c + shb[0] + T//2, c + shb[1] - T//2:c + shb[1] + T//2].std()
    rows.append((ra, rb, rk, k2))
    print(f"   {t:5d} {fi:6d} {k2:7.3f} | {ra:12.4f} {rb:9.4f} | "
          f"{'default' if ra > rb else 'b0x4':>8}  {aa:7.5f} {bb_:7.5f}")
    if t == order[0]:
        c = WIN // 2
        pr = stretch(acc[c-T//2:c+T//2, c-T//2:c+T//2] / len(idxs))
        pa = stretch(ma[sy, sx][c+sha[0]-T//2:c+sha[0]+T//2, c+sha[1]-T//2:c+sha[1]+T//2])
        pb = stretch(mb[sy, sx][c+shb[0]-T//2:c+shb[0]+T//2, c+shb[1]-T//2:c+shb[1]+T//2])
        img = np.concatenate([pr, np.ones((T, 8)), pa, np.ones((T, 8)), pb], axis=1)
        p = os.path.join(OUT, "crops", f"{KEY}-groundtruth-tile{t}.png")
        Image.fromarray((img * 255).astype(np.uint8)).resize(
            (img.shape[1] * 3, img.shape[0] * 3), Image.NEAREST).save(p)
        print(f"   wrote {p}   [ REAL FRAME | default | b0x4 ]")

ra = np.array([r[0] for r in rows]); rb = np.array([r[1] for r in rows])
rk = np.array([r[2] for r in rows]); k2 = np.array([r[3] for r in rows])
print(f"\n   K0 PASS (rho(ref,ref)=1.000000 on every tile)")
print(f"   K1 in-focus {ra.mean():.4f} vs defocused {rk.mean():.4f}  "
      f"{'PASS' if ra.mean() > rk.mean() + 0.15 else 'FAIL'}")
print(f"   K2 5-frame ref keeps {k2.mean():.3f} of single-frame band amplitude  "
      f"{'PASS' if k2.mean() > 0.70 else 'FAIL - averaging blurred the reference'}")
print(f"\n   MEAN rho to ground truth: default {ra.mean():.4f}  b0x4 {rb.mean():.4f}  "
      f"delta {rb.mean()-ra.mean():+.4f}")
print(f"   default closer to truth on {int((ra>rb).sum())}/{len(rows)} tiles")
