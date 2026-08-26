"""Independent, tone-invariant sharpness instrument + commissioning.

Re-CHOOSES the statistic rather than re-computing BUILD-RENDER's.
Spectrum shape: normalise the radial power spectrum by TOTAL power, so any
global gain divides out exactly, then read the high-frequency fraction.
Unlike standardisation (gain+offset only), this is also tested against a
NONLINEAR tone curve, which standardisation does not remove.
"""
import numpy as np
from pathlib import Path
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

def luma(p):
    a = np.asarray(Image.open(p).convert("RGB"))
    assert a.dtype == np.uint8, f"expected uint8 JPEG, got {a.dtype}"
    return a.astype(np.float64).mean(2)

def gauss(y, s):
    if s <= 0: return y.copy()
    r = int(np.ceil(4*s)); x = np.arange(-r, r+1)
    k = np.exp(-x**2/(2*s*s)); k /= k.sum()
    o = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 1, y)
    return np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 0, o)

def grad_rms(y):
    return float(np.sqrt(np.diff(y,axis=1).var() + np.diff(y,axis=0).var()))

def grad_rms_norm(y):
    s = y.std()
    return 0.0 if s < 1e-9 else grad_rms((y - y.mean())/s)

_RCACHE = {}
def hf_fraction(y, lo=0.25, hi=0.45):
    """Fraction of total spectral power in an annulus. Global gain cancels."""
    h, w = y.shape
    key = (h, w)
    if key not in _RCACHE:
        fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.fftfreq(w)[None, :]
        _RCACHE[key] = np.sqrt(fy**2 + fx**2) / 0.5   # 1.0 == Nyquist
        wy = np.hanning(h)[:, None]; wx = np.hanning(w)[None, :]
        _RCACHE[(key, "win")] = wy * wx
    r = _RCACHE[key]; win = _RCACHE[(key, "win")]
    z = (y - y.mean()) * win
    p = np.abs(np.fft.fft2(z))**2
    tot = p.sum()
    if tot <= 0: return 0.0
    return float(p[(r >= lo) & (r < hi)].sum() / tot)

if __name__ == "__main__":
    src = Path(r"C:\dev\strehl-out\gallery-history\2026-08-25-tone-fix\couch-fibers-cpl.jpg")
    y = luma(src)
    print(f"commissioning image: {src.name}  shape={y.shape}  mean={y.mean():.2f} sd={y.std():.2f}\n")

    def arm(name, z):
        return (name, grad_rms(z)/grad_rms(y), grad_rms_norm(z)/grad_rms_norm(y),
                hf_fraction(z)/hf_fraction(y))

    arms = [
        arm("A null: identical image", y.copy()),
        arm("B blur sigma=0.5 (must DETECT)", gauss(y, 0.5)),
        arm("B2 blur sigma=1.0 (must DETECT)", gauss(y, 1.0)),
        arm("C linear gain x0.95 (must IGNORE)", y*0.95),
        arm("D gamma 1.20 NONLINEAR (must IGNORE)", 255.0*np.clip(y/255.0,0,1)**1.20),
        arm("E gamma 0.85 NONLINEAR (must IGNORE)", 255.0*np.clip(y/255.0,0,1)**0.85),
        arm("F S-curve NONLINEAR (must IGNORE)",
            255.0*np.clip(0.5-0.5*np.cos(np.pi*np.clip(y/255.0,0,1)),0,1)),
    ]
    print(f"{'arm':38s} {'gradRMS':>9s} {'gradNORM':>9s} {'HFfrac':>9s}")
    print("-"*70)
    for n, a, b, c in arms:
        print(f"{n:38s} {a:9.4f} {b:9.4f} {c:9.4f}")
    print("\nreading: 1.0000 == statistic did not move.")
    print("A statistic that moves on rows D/E/F is reading the TONE CURVE, not sharpness.")
