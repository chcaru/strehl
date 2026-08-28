"""V-KILLB0 ground.py -- GROUND TRUTH test.  Which arm matches the real frame?

The one defence left for the leaf-2 result is: "default is the broken arm; the
extra amplitude it carries at structured sites is merge artefact, and b0x4 is
the clean one."  That defence is testable, because for any structured tile
there exists a SOURCE FRAME in which that tile is genuinely in focus, and that
frame is ground truth for what the scene contains there.

Method: for each structured tile, use the harvested selection-band power to
find the develop frame where that tile peaks (in focus).  Bandpass the develop
tile and both master tiles in 0.05-0.14 cyc/px -- qualified SIGNAL at
structured sites on leaf-2 (R = 48.1 and 19.1, both PASS) -- and ask which
master correlates better with the real frame.

TONE: the develops are linear and the masters are sRGB-encoded, so absolute rho
is depressed by the tone mismatch.  That mismatch is IDENTICAL for both arms, so
rho_default vs rho_b0x4 is a fair comparison; the absolute values are not to be
read as absolute fidelity.

ALIGNMENT: develops are unaligned (STREHL_ALIGN=0), masters are registered, so
each arm gets an INDEPENDENT integer shift search and is scored at its own best
shift.  Scoring each arm at its own optimum cannot favour either one.

CONTROLS:
  K0  rho(develop, develop)            must be 1.000000
  K1  rho(defocused develop, default)  must be far below rho(in-focus, default)
      -- if it is not, the "in focus" frame index means nothing and the test is
      dead.
"""
import os
import sys

import numpy as np
import tifffile

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


def radial(img, f0, f1):
    a = np.fft.rfft2(img.astype(np.float64))
    h, w = img.shape
    r = np.hypot(np.fft.fftfreq(h)[:, None], np.fft.rfftfreq(w)[None, :])
    a *= ((r >= f0) & (r < f1))
    return np.fft.irfft2(a, s=img.shape)


def best_rho(ref, arm):
    """rho between ref and arm at the integer shift that maximises it."""
    c = WIN // 2
    r = ref[c - T // 2:c + T // 2, c - T // 2:c + T // 2]
    r = r - r.mean()
    er = np.sqrt((r * r).mean())
    bb, bs = -2.0, None
    for dy in range(-SEARCH, SEARCH + 1, 4):
        for dx in range(-SEARCH, SEARCH + 1, 4):
            a = arm[c + dy - T // 2:c + dy + T // 2, c + dx - T // 2:c + dx + T // 2]
            a = a - a.mean()
            ea = np.sqrt((a * a).mean())
            if ea == 0:
                continue
            v = (r * a).mean() / (er * ea)
            if v > bb:
                bb, bs = v, (dy, dx, ea / er)
    return bb, bs


files = sorted(f for f in os.listdir(DEV) if f.lower().endswith(".tif"))
step_dev = max(1, round(len(files) / 80))
selp = np.load(os.path.join(OUT, f"{KEY}-selp.npy"))
mm = tifffile.memmap(os.path.join(DEV, files[0]), mode="r")
H, W = mm.shape[0], mm.shape[1]
del mm
ys = np.linspace(MARGIN, H - MARGIN - T, NY).astype(int)
xs = np.linspace(MARGIN, W - MARGIN - T, NX).astype(int)
pos = [(int(y), int(x)) for y in ys for x in xs]

peak = np.nanmax(selp, axis=0)
order = np.argsort(-peak)
print(f"== GROUND TRUTH {KEY}   band {F0}-{F1} cyc/px (PASS at structured sites: R=48.1, 19.1)")
print(f"   develops={len(files)} step={step_dev}  masters vs the real in-focus frame\n")

ma = h2.luma709(tifffile.imread(os.path.join(OUT, "default", KEY + ".tiff"))[..., :3].astype(np.float64))
mb = h2.luma709(tifffile.imread(os.path.join(OUT, "b0x4", KEY + ".tiff"))[..., :3].astype(np.float64))
print(f"   master shape {ma.shape}   develop shape ({H}, {W})")

print(f"   {'tile':>5} {'y':>6} {'x':>6} {'frame':>6} | {'rho DEFAULT':>12} {'amp':>6} "
      f"| {'rho b0x4':>9} {'amp':>6} | {'K1 defocus rho':>15}")
rows = []
for t in order[:8]:
    y, x = pos[t]
    fi = int(np.nanargmax(selp[:, t]) * step_dev)
    lo = int(np.nanargmin(selp[:, t]) * step_dev)
    cy, cx = y + T // 2, x + T // 2
    sl = (slice(cy - WIN // 2, cy + WIN // 2), slice(cx - WIN // 2, cx + WIN // 2))
    dv = radial(h2.luma709(np.asarray(tifffile.memmap(os.path.join(DEV, files[fi]), mode="r")[sl[0], sl[1], :3], np.float64)), F0, F1)
    df = radial(h2.luma709(np.asarray(tifffile.memmap(os.path.join(DEV, files[lo]), mode="r")[sl[0], sl[1], :3], np.float64)), F0, F1)
    A = radial(ma[sl], F0, F1)
    B = radial(mb[sl], F0, F1)
    ra, sa = best_rho(dv, A)
    rb, sb = best_rho(dv, B)
    rk, _ = best_rho(df, A)
    k0 = best_rho(dv, dv)[0]
    if abs(k0 - 1.0) > 1e-6:
        raise SystemExit(f"K0 NULL FAILED: rho(dev,dev)={k0}")
    rows.append((ra, rb, rk))
    print(f"   {t:5d} {y:6d} {x:6d} {fi:6d} | {ra:12.4f} {sa[2]:6.3f} "
          f"| {rb:9.4f} {sb[2]:6.3f} | {rk:15.4f}")

ra = np.array([r[0] for r in rows]); rb = np.array([r[1] for r in rows])
rk = np.array([r[2] for r in rows])
print(f"\n   K0 rho(develop,develop) = 1.000000 on every tile   PASS")
print(f"   K1 in-focus rho {ra.mean():.4f} vs defocused-frame rho {rk.mean():.4f}   "
      f"{'PASS' if ra.mean() > rk.mean() + 0.15 else 'FAIL - focus index is meaningless'}")
print(f"\n   MEAN rho to ground truth:  default {ra.mean():.4f}   b0x4 {rb.mean():.4f}   "
      f"delta {rb.mean()-ra.mean():+.4f}")
print(f"   b0x4 matches the real frame better on {int((rb>ra).sum())}/{len(rows)} tiles")
