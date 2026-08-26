"""C8: how much does VA move if the two tiles span DIFFERENT scene content?

C3 proved VA is immune to the two arms SAMPLING the same span at different
densities. This is the other error: getting the span itself wrong, which is
what a registration scale error does. If VA is not immune to this, the whole
measurement is hostage to the registration and must say so.
"""
import pathlib, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vstat import va_blur_px
import tifffile
from vplant import gauss_exact

def synth(N, K=200, alpha=2.5, seed=7, blur_px=0.0, Tref=800, span=1.0):
    """Sample a band-limited scene over `span` times the reference span."""
    rng = np.random.default_rng(seed)
    Z = np.zeros((N, N), dtype=complex)
    sig_s = blur_px/float(Tref)
    for ky in range(-K, K+1):
        for kx in range(0, K+1):
            if kx == 0 and ky <= 0: continue
            k = np.hypot(ky, kx)
            if k > K or k < 1: continue
            v = (k**(-alpha/2.0))*(rng.normal()+1j*rng.normal())
            v *= np.exp(-2.0*np.pi**2*sig_s**2*k*k)
            kk_y, kk_x = ky, kx
            Z[kk_y % N, kk_x % N] = v
            Z[(-kk_y) % N, (-kk_x) % N] = np.conj(v)
    f = np.fft.ifft2(Z).real*(N*N)
    if span != 1.0:                       # crop/extend the sampled window
        n2 = int(round(N*span))
        if n2 <= N:
            o = (N-n2)//2
            return f[o:o+n2, o:o+n2]
    return f

print("C8  SPAN ERROR: the argmax tile covers (1+eps) of the merge tile's scene")
print("    correct answer 0.000 at every eps; a real registration scale error")
print("    of 5.8% (flowers, logged 0.9367 vs fitted 0.9909) is eps ~ 0.058.")
m = synth(800)
print(f"    {'eps':>8}{'Ta used':>9}{'VA':>10}")
for eps in (0.0, 0.005, 0.01, 0.02, 0.04, 0.06, 0.10):
    # argmax arm: same scene, sampled at 739 px per merge-span, but we CUT a tile
    # that actually spans (1+eps) of the merge tile and treat it as if it spanned 1.
    Ta = int(round(800*0.9236*(1+eps)))
    a = synth(Ta, Tref=800)
    print(f"    {eps:>8.3f}{Ta:>9}{va_blur_px(m, a, denoise=False):>10.3f}")

print("\n    ...and with a real 0.40 px blur planted on top (must still read ~0.40)")
for eps in (0.0, 0.02, 0.06):
    Ta = int(round(800*0.9236*(1+eps)))
    a = synth(Ta, Tref=800, blur_px=0.40)
    print(f"    eps {eps:.3f} -> {va_blur_px(m, a, denoise=False):+.3f}")

print("\nC9  REAL TILES: VA vs the span it was given (empirical sensitivity)")
R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
gm = tifffile.imread(str(R/"flat-on-ruler-cpl"/"merge.tif"))[:,:,1].astype(np.float64)
t = gm[1000:1800, 1400:2200]
print("    merge tile vs an exact-Gaussian-blurred copy cut at the WRONG span")
for eps in (0.0, 0.01, 0.02, 0.04):
    n = int(round(800*(1+eps)))
    big = gm[1000:1000+n, 1400:1400+n]
    print(f"    eps {eps:+.2f}: VA(t, blur0.5(bigger crop)) = "
          f"{va_blur_px(t, gauss_exact(big,0.5)):+.3f}  (truth +0.50)")
