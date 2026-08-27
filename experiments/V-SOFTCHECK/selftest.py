"""Unit checks on the instrument's own primitives."""
import numpy as np, softcheck as S
from scipy import ndimage
rng = np.random.default_rng(0); ok = True

# 1. tile_means (integral image) == direct mean
x = rng.standard_normal((400, 500)).astype(np.float32)
oy = np.array([0, 37, 200, 271]); ox = np.array([0, 91, 300, 371]); T = 64
a = S.tile_means(x, oy, ox, T)
b = np.array([x[oy[i]:oy[i]+T, ox[i]:ox[i]+T].mean() for i in range(len(oy))])
e = np.abs(a-b).max(); print(f"tile_means max abs err {e:.3e}", "PASS" if e < 1e-9 else "FAIL"); ok &= e < 1e-9

# 2. white-noise gain: E[dog(n)^2] == sigma^2 * G
n = rng.standard_normal((2048, 2048)).astype(np.float32) * 7.0
for s, g in ((S.S_MID, S.G_MID), (S.S_HI, S.G_HI)):
    m = (S.dog(n, s)**2).mean(); pred = 49.0*g
    r = m/pred; print(f"  white gain {s}: measured {m:.4f} predicted {pred:.4f} ratio {r:.4f}",
                      "PASS" if abs(r-1) < 0.02 else "FAIL"); ok &= abs(r-1) < 0.02

# 3. c_noise cancels pure white noise exactly
sub = (S.dog(n, S.S_MID)**2).mean() - S.C_NOISE*(S.dog(n, S.S_HI)**2).mean()
print(f"  SUB on pure white noise = {sub:+.4f} (target 0; scale {49*S.G_MID:.2f})",
      "PASS" if abs(sub) < 0.02*49*S.G_MID else "FAIL"); ok &= abs(sub) < 0.02*49*S.G_MID

# 4. register recovers a planted similarity
base = ndimage.gaussian_filter(rng.standard_normal((2344, 3516)).astype(np.float32), 1.2)*1000+8000
yy, xx = np.mgrid[0:2344, 0:3516].astype(np.float32)
sc, ty, tx = 0.9940, -3.5, +6.25
warp = ndimage.map_coordinates(base, [(yy-1172)/sc+1172-ty, (xx-1758)/sc+1758-tx], order=3, mode="reflect")
coef, rms, kp, tot = S.register(base, warp.astype(np.float32))
pred_sy = 1+coef[1,0]; pred_sx = 1+coef[2,1]
d = S.disp_at(coef, np.array([1172.0]), np.array([1758.0]))[0]
print(f"  planted scale {sc:.4f} recovered sy={pred_sy:.4f} sx={pred_sx:.4f}; "
      f"planted centre shift ({ty:+.2f},{tx:+.2f}) recovered ({d[0]:+.2f},{d[1]:+.2f}); rms {rms:.2f}px")
g = abs(pred_sy-sc) < 6e-4 and abs(pred_sx-sc) < 6e-4 and abs(d[0]-ty) < 1.5 and abs(d[1]-tx) < 1.5
print("  register", "PASS" if g else "FAIL"); ok &= g
print("SELFTEST", "PASS" if ok else "FAIL")
