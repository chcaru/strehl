"""V-THESIS instrument commissioning, take 2, with EXACT plants.

Take 1 used scipy.ndimage.gaussian_filter and produced an apparent dead zone
below 0.3 px. plant_audit.py showed that was the PLANT, not the instrument:
that filter is the identity at sigma <= 0.12 and MTF^2 = 0.99997 at sigma=0.20.
Everything below is planted with an exact Fourier Gaussian instead.
"""
import pathlib, sys
import numpy as np, tifffile

sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vstat import va_blur_px, vb_f50_scene, sigma_immerkaer          # noqa: E402
from vplant import gauss_exact, scale_exact, despeckle               # noqa: E402
sys.path.insert(0, str(pathlib.Path("experiments/BUILD-THESIS").resolve()))
from stats import STATS as BT_STATS                                  # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
RNG = np.random.default_rng(90210)


def tile(subject, y, x, n, arm="merge"):
    return tifffile.imread(str(R / subject / f"{arm}.tif"))[y:y+n, x:x+n, 1].astype(np.float64)


def va(tm, ta, ds=True):
    if ds:
        tm, _ = despeckle(tm, sigma_immerkaer(tm))
        ta, _ = despeckle(ta, sigma_immerkaer(ta))
    return va_blur_px(tm, ta)


def synth(N, K=200, alpha=2.5, seed=7, blur_px=0.0, Tref=800):
    rng = np.random.default_rng(seed)
    Z = np.zeros((N, N), dtype=complex)
    sig_s = blur_px / float(Tref)
    for ky in range(-K, K+1):
        for kx in range(0, K+1):
            if kx == 0 and ky <= 0: continue
            k = np.hypot(ky, kx)
            if k > K or k < 1: continue
            v = (k ** (-alpha/2.0)) * (rng.normal() + 1j*rng.normal())
            v *= np.exp(-2.0*np.pi**2*sig_s**2*k*k)
            Z[ky % N, kx % N] = v
            Z[(-ky) % N, (-kx) % N] = np.conj(v)
    return np.fft.ifft2(Z).real * (N*N)


print("="*80); print("V-THESIS COMMISSIONING (exact plants)"); print("="*80)
t = tile("leaf-2-cpl", 900, 1400, 800)
s0 = sigma_immerkaer(t)
print(f"real tile leaf-2-cpl merge[900:1700,1400:2200]  mean {t.mean():.0f} DN  sigma {s0:.2f} DN")

print("\nC1  IDENTITY                          (must be exactly 0.000)")
print(f"    VA(t,t) = {va(t,t):+.4f} px")

print("\nC2  EXACT GAUSSIAN PLANT, same sampling, REAL NOISY TILE")
print(f"    {'planted':>8}{'VA':>10}{'error':>9}   |   BUILD-THESIS statistics, ratio arg/merge")
print(f"    {'':>8}{'':>10}{'':>9}   |{'S1':>10}{'S2':>10}{'S3':>10}")
base = {k: fn(t) for k, fn in BT_STATS.items()}
for s in (0.05,0.10,0.15,0.20,0.30,0.40,0.50,0.80,1.20,2.00):
    tb = gauss_exact(t, s)
    got = va(t, tb)
    rat = "".join(f"{BT_STATS[k](tb)/base[k]:>10.5f}" for k in BT_STATS)
    print(f"    {s:>8.2f}{got:>10.3f}{got-s:>+9.3f}   |{rat}")

print("\nC2b SIGN TEST (merge made blurrier -> must be NEGATIVE)")
for s in (0.20,0.50):
    print(f"    merge blurred {s:.2f} -> {va(gauss_exact(t,s), t):+.3f}")

print("\nC3  PURE SCALE, ZERO BLUR: two samplings of ONE band-limited scene")
print("    correct answer 0.000. The BUILD-THESIS columns are the CONTROL:")
print("    they show whether a per-pixel statistic can express this confound.")
print(f"    {'s':>8}{'Ta':>6}{'VA':>10}   |{'S1 a/m':>10}{'S2 a/m':>10}{'S3 a/m':>10}")
for s in (0.9236,0.9321,0.9707):
    Ta = int(round(800*s))
    m, a = synth(800), synth(Ta)
    r = "".join(f"{BT_STATS[k](a)/BT_STATS[k](m):>10.4f}" for k in BT_STATS)
    print(f"    {s:>8.4f}{Ta:>6}{va_blur_px(m,a,denoise=False):>10.3f}   |{r}")

print("\nC4  EXACT BLUR ACROSS A SCALE MISMATCH (must still recover)")
print(f"    {'s':>8}{'planted':>9}{'VA':>10}{'error':>9}")
for s in (0.9236,0.9707):
    Ta = int(round(800*s))
    m = synth(800)
    for sig in (0.20,0.30,0.60,1.00):
        a = synth(Ta, blur_px=sig, Tref=800)
        g = va_blur_px(m,a,denoise=False)
        print(f"    {s:>8.4f}{sig:>9.2f}{g:>10.3f}{g-sig:>+9.3f}")

print("\nC5  GAUSSIAN NOISE NULL at the real sigma ratios (must be 0.000)")
print(f"    {'ratio':>8}{'VA':>10}{'VA no floor sub':>18}")
for r in (1.064,1.078,1.110,1.381,1.625,2.681):
    add = float(np.sqrt(max((r*s0)**2 - s0**2, 0.0)))
    tn = t + RNG.normal(0.0, add, t.shape)
    print(f"    {r:>8.3f}{va(t,tn):>10.3f}{va_blur_px(t,tn,denoise=False):>18.3f}")

print("\nC5b IMPULSE NULL, 0.05% salt-and-pepper (must be 0.000 after despeckle)")
tn = t.copy(); flat = tn.ravel()
idx = RNG.choice(t.size, int(0.0005*t.size), replace=False)
flat[idx] = np.where(RNG.random(idx.size) < 0.5, t.min(), t.max())
print(f"    no despeckle : {va(t,tn,ds=False):+.3f} px")
print(f"    despeckled   : {va(t,tn,ds=True):+.3f} px")
_, fr_clean = despeckle(t, s0); _, fr_imp = despeckle(tn, s0)
print(f"    fraction replaced: clean {fr_clean*100:.4f}%   impulsed {fr_imp*100:.4f}%")

print("\nC5c DESPECKLE MUST NOT EAT REAL DETAIL: C2 ladder re-run with despeckle ON/OFF")
for s in (0.20,0.50,1.00):
    tb = gauss_exact(t,s)
    print(f"    planted {s:.2f}:  off {va(t,tb,ds=False):+.3f}   on {va(t,tb,ds=True):+.3f}")

print("\nC6  DETECTION FLOOR (exact plants)")
for s in (0.02,0.05,0.08,0.10,0.15,0.20):
    print(f"    planted {s:.2f} -> {va(t, gauss_exact(t,s)):+.4f}")
