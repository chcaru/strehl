r"""What band does gf_discriminate's detail channel actually occupy?

band_rms() = gaussian(g,1.4) - gaussian(g,2.8). Its passband is computed here
numerically from the 2D transfer function, not from a closed form I might get
wrong, and cross-checked against a direct measurement on sinusoidal gratings.
"""
import numpy as np
from scipy.ndimage import gaussian_filter

S1, S2 = 1.4, 2.8

# analytic transfer function of the DoG, f in cycles/pixel
f = np.linspace(1e-4, 0.5, 20001)
H = np.exp(-2*np.pi**2*S1**2*f**2) - np.exp(-2*np.pi**2*S2**2*f**2)
pk = f[np.argmax(H)]
hm = H.max()/2.0
above = f[H >= hm]
lo, hi = above.min(), above.max()
# half-POWER (-3dB) edges as well, since the statistic is an RMS of the band
hp = H.max()/np.sqrt(2.0)
ap = f[H >= hp]

print("gf_discriminate detail band: DoG(sigma=%.1f, %.1f)" % (S1, S2))
print("  peak response      : %.4f cyc/px" % pk)
print("  half-amplitude span: %.4f - %.4f cyc/px" % (lo, hi))
print("  half-power   span  : %.4f - %.4f cyc/px" % (ap.min(), ap.max()))

# empirical check: push real gratings through the actual filter
print("\n  empirical check on sinusoidal gratings (same code path):")
N = 512
y, x = np.mgrid[0:N, 0:N].astype(np.float64)
best = (0, -1)
for ftest in (0.05, 0.109, 0.15, 0.20, 0.30, 0.35, 0.40):
    g = np.sin(2*np.pi*ftest*x)
    b = gaussian_filter(g, S1) - gaussian_filter(g, 2.0*S1)
    r = float(np.sqrt(np.mean(b[64:-64, 64:-64]**2)))
    if r > best[1]: best = (ftest, r)
    print("     %.3f cyc/px -> rms %.5f  (%.1f%% of peak-analytic %.5f)"
          % (ftest, r, 100*r/(H.max()/np.sqrt(2)), H.max()/np.sqrt(2)))
print("     empirical peak among tested: %.3f cyc/px" % best[0])

print("\n  ORCH: corpus signal/noise boundary moves 0.17 - 0.48 cyc/px.")
print("  my band's half-power upper edge %.4f vs corpus MINIMUM boundary 0.17 -> %s"
      % (ap.max(), "BELOW on every subject" if ap.max() < 0.17 else "OVERLAPS"))
print("  disputed slice 0.30-0.35 lies at %.1f%% of my band's peak response"
      % (100*np.interp(0.325, f, H)/H.max()))