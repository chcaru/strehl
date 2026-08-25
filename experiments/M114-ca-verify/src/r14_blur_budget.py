"""M114 r14: isolate RESAMPLING ATTENUATION from misregistration.

r13's G2 bar was the wrong instrument and it failed: high-frequency energy
measured on a GREEN-defined edge mask is dominated by how far red sits from
green, not by how blurred red is. The placebo displaces red 1.4-2.5 px, so its
hf energy rose +25% -- that is misregistration, not sharpness.

A rigid shift does not change an image's total high-frequency energy; only
resampling attenuation does. So measure hf energy GLOBALLY, over the whole
frame, with no mask. Then the placebo and the correction -- which resample by
identical magnitudes -- must show identical attenuation, and any difference
between `off` and them is the blur ORCH is asking about.

STRUCTURAL NOTE, verified by reading align_cmd.rs:1274-1298: each of the four
CFA planes is gathered EXACTLY ONCE via gather_checked(src, t_site, ...) whether
or not a profile is active. `compose` returns `t` untouched when ca is None. So
the correction adds NO extra interpolation pass; it changes the transform of a
gather that already happens. It can only alter the fractional sampling phase.

BARS
  H1  NULL ON THE STATISTIC. `off` measured against itself must read 0.000%.
  H2  ATTENUATION MATCHED. on and tan resample by identical magnitude, so their
      global R attenuation vs off must agree within 2 percentage points. If they
      do not, global hf energy is not measuring attenuation either and H3 is
      void.
  H3  THE ANSWER. Global R attenuation in `on` vs `off` = the entire blur budget
      the correction could possibly have borrowed.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage
from pathlib import Path

R12 = Path(r"C:\dev\strehl-out\M114-ca-verify\r12")
off = tifffile.imread(str(R12 / "off.tif")).astype(np.float64)
on = tifffile.imread(str(R12 / "on.tif")).astype(np.float64)
tan = tifffile.imread(str(R12 / "tan.tif")).astype(np.float64)
H, W, _ = off.shape

def hp(x):
    return x - ndimage.uniform_filter(x, 5)

def ghf(a, c):
    return float(np.mean(np.abs(hp(a[:, :, c]))))

print("GLOBAL high-frequency energy, whole frame, no mask")
print("chan        off          on        d%%          tan         d%%")
res = {}
for c, nm in [(0, "R"), (1, "G"), (2, "B")]:
    o, n, t = ghf(off, c), ghf(on, c), ghf(tan, c)
    res[nm] = dict(off=o, on=n, tan=t, on_pct=100 * (n / o - 1), tan_pct=100 * (t / o - 1))
    print("%s     %10.4f  %10.4f  %+7.3f%%  %10.4f  %+7.3f%%" % (nm, o, n, 100 * (n / o - 1), t, 100 * (t / o - 1)))

h1 = abs(100 * (ghf(off, 0) / ghf(off, 0) - 1)) < 1e-9
print("\nH1 null (off vs itself)                       : %s" % ("PASS" if h1 else "FAIL"))
dn, dt = res["R"]["on_pct"], res["R"]["tan_pct"]
h2 = abs(dn - dt) <= 2.0
print("H2 on/tan R attenuation agree within 2 pp     : %s  (%.3f vs %.3f, gap %.3f pp)"
      % ("PASS" if h2 else "FAIL", dn, dt, abs(dn - dt)))
print("H3 TOTAL blur budget the correction could have borrowed: %+.3f%% of R hf energy" % dn)

# ---- the speckle statistic, done right: chroma variance in FLAT areas ----
gof = off[:, :, 1]
edge = ndimage.gaussian_gradient_magnitude(gof, 1.2)
flat = edge < np.percentile(edge, 60.0)
def speck(a):
    y = 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
    return float(np.std(hp(a[:, :, 0] - y)[flat]))
so, sn, st = speck(off), speck(on), speck(tan)
print("\nchroma speckle (sd of hp(R-Y)) in FLAT areas, %d px" % flat.sum())
print("  off %.4f   on %.4f (%+.2f%%)   tan %.4f (%+.2f%%)"
      % (so, sn, 100 * (sn / so - 1), st, 100 * (st / so - 1)))

res.update(dict(H1=bool(h1), H2=bool(h2), blur_budget_pct=dn,
                speckle=dict(off=so, on=sn, tan=st)))
(R12 / "r14.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
