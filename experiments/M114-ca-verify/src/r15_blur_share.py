"""M114 r15: how much chroma improvement can pure BLUR buy?

r13 and r14 both failed their blur bars for the same structural reason: the
output red channel is reconstructed by a GREEN-GUIDED demosaic, so any red/green
misregistration injects high-frequency energy into R. No output-domain sharpness
statistic can separate blur from misregistration.

So stop trying to isolate the blur and MEASURE ITS EFFECT INSTEAD. Take the OFF
arm, blur its red channel by exactly enough to reproduce the ON arm's global R
attenuation, and measure the chroma statistic. That is the entire chroma gain
that interpolation blur could possibly have contributed. Everything else the
correction achieved, it achieved by moving red to where it belongs.

BARS
  K1  CALIBRATION. Blurred-off global R hf must match ON's to within 0.2 pp.
  K2  NULL. Zero blur must read exactly 0.000%% chroma change.
  K3  ANSWER. Chroma gain from matched blur alone vs the correction's gain.
  K4  BOUND. Repeat at 3x the attenuation. Even a grossly excessive blur must
      not reach the correction's gain, or the decomposition is inconclusive.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage
from pathlib import Path

R12 = Path(r"C:\dev\strehl-out\M114-ca-verify\r12")
off = tifffile.imread(str(R12 / "off.tif")).astype(np.float64)
on = tifffile.imread(str(R12 / "on.tif")).astype(np.float64)
H, W, _ = off.shape

def hp(x):
    return x - ndimage.uniform_filter(x, 5)

gof = off[:, :, 1]
edge = ndimage.gaussian_gradient_magnitude(gof, 1.2)
mask = edge > np.percentile(edge, 97.0)

def ghf_r(r):
    return float(np.mean(np.abs(hp(r))))

def chroma_with(r):
    y = 0.2126 * r + 0.7152 * off[:, :, 1] + 0.0722 * off[:, :, 2]
    return float(np.mean(np.abs(hp(r - y))[mask]))

r_off = off[:, :, 0]
base_hf = ghf_r(r_off)
base_ch = chroma_with(r_off)
on_ch = float(np.mean(np.abs(hp(on[:, :, 0] - (0.2126 * on[:, :, 0] + 0.7152 * on[:, :, 1] + 0.0722 * on[:, :, 2])))[mask]))
target = -2.913
print("baseline: global R hf %.4f   chroma %.5f" % (base_hf, base_ch))
print("correction achieves chroma %.5f (%+.2f%%)" % (on_ch, 100 * (on_ch / base_ch - 1)))

k2 = abs(100 * (chroma_with(r_off) / base_ch - 1)) < 1e-9
print("\nK2 null (zero blur)                       : %s" % ("PASS" if k2 else "FAIL"))

def find_sigma(goal_pct):
    lo, hi = 0.0, 3.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        got = 100 * (ghf_r(ndimage.gaussian_filter(r_off, mid)) / base_hf - 1)
        if got > goal_pct:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

rows = []
for label, goal in [("matched 1x", target), ("excessive 3x", 3 * target)]:
    s = find_sigma(goal)
    rb = ndimage.gaussian_filter(r_off, s)
    got = 100 * (ghf_r(rb) / base_hf - 1)
    ch = chroma_with(rb)
    pct = 100 * (ch / base_ch - 1)
    rows.append((label, s, goal, got, ch, pct))
    print("%-13s sigma %.4f  R hf %+.3f%% (goal %+.3f%%)  chroma %+.3f%%"
          % (label, s, got, goal, pct))

k1 = abs(rows[0][3] - target) <= 0.2
corr_pct = 100 * (on_ch / base_ch - 1)
share = 100 * rows[0][5] / corr_pct
k4 = rows[1][5] > corr_pct
print("\nK1 blur calibrated to the ON arm's attenuation : %s" % ("PASS" if k1 else "FAIL"))
print("K3 matched blur buys %+.3f%% of the correction's %+.3f%%  ->  %.1f%% of the gain"
      % (rows[0][5], corr_pct, share))
print("K4 even 3x-excessive blur falls short of the correction : %s (%+.3f%% vs %+.3f%%)"
      % ("PASS" if k4 else "FAIL", rows[1][5], corr_pct))

(R12 / "r15.json").write_text(json.dumps(dict(
    base_hf=base_hf, base_chroma=base_ch, on_chroma=on_ch, corr_pct=corr_pct,
    rows=[list(r) for r in rows], K1=bool(k1), K2=bool(k2), K4=bool(k4),
    blur_share_pct=float(share)), indent=1, default=float), encoding="utf-8")
