"""Shared helpers for M95 arm 2: chroma co-siting in the binned output.

THE HYPOTHESIS UNDER TEST
-------------------------
strehl's default output bins each 2x2 RGGB quad to one RGB pixel:

    R  = R(2px,   2py)
    G  = (G1(2px+1, 2py) + G2(2px, 2py+1)) / 2
    B  = B(2px+1, 2py+1)

In sensor coordinates the quad centre is (2px+0.5, 2py+0.5). So:

    green  centroid = (2px+0.5, 2py+0.5)  -> EXACTLY the quad centre
    red    site     = (2px+0.0, 2py+0.0)  -> centre + (-0.5, -0.5) sensor px
    blue   site     = (2px+1.0, 2py+1.0)  -> centre + (+0.5, +0.5) sensor px

Those three samples are then written into one pixel as if they were co-sited.
They are not. Red leads blue by exactly one sensor pixel along the main
diagonal, which in the binned output grid is HALF an output pixel:

    predicted displacement of B relative to R = (+0.5, +0.5) binned px

This module measures that displacement directly, and the demosaiced render of
the same frame is the control: Malvar-He-Cutler estimates all three channels at
every photosite, so it co-sites them and the constant term must collapse.

THE CONFOUND, AND HOW IT IS SEPARATED
-------------------------------------
Lateral chromatic aberration also displaces R against B. It cannot be assumed
away. It is separated by its field signature: the binning defect is a CONSTANT
vector everywhere in the frame, while LCA is radial -- zero at the optical
centre and growing outward, pointing along the radius. Measuring at many field
positions and fitting

    d(x, y) = c + k * r_hat(x, y)

splits them. `c` is the binning defect; `k` is the lens.

THE ESTIMATOR
-------------
Sub-pixel shift by fitting the PHASE RAMP of the cross-power spectrum, rather
than by parabolic interpolation of a correlation peak. For a pure translation
`b(x) = a(x - d)`,

    B(f) = A(f) * exp(-2*pi*i * f . d)

so the cross-power spectrum `conj(A) * B` has phase `-2*pi*(f . d)`, linear in
frequency through the origin. A magnitude-weighted least-squares fit of that
plane recovers `d` with no peak-interpolation bias, which matters here because
the effect being measured IS half a pixel.

Written from that definition. `skimage.registration.phase_cross_correlation`
is used only as an INDEPENDENT CROSS-CHECK in the controls, never as the
primary instrument.
"""

import json
import os

import numpy as np

OUT = r"C:\dev\strehl-out\M93-out"  # M93-era scratch; kept, see M95 report S0
IMG = r"C:\dev\strehl-out\M95-chroma-cositing"
HERE = os.path.dirname(os.path.abspath(__file__))
JSON = os.path.join(os.path.dirname(HERE), "out")

BINNED_W, BINNED_H = 3516, 2344


def hann2(h, w):
    """Separable Hann window. Kills the wrap-around edge discontinuity that
    would otherwise put a cross-shaped artifact through the whole spectrum and
    bias a phase fit."""
    wy = np.hanning(h + 2)[1:-1]
    wx = np.hanning(w + 2)[1:-1]
    return np.outer(wy, wx)


def highpass(a, sigma):
    """Remove structure coarser than `sigma` px.

    The R and B channels of a real scene differ by the scene's own colour at
    low frequency, and that difference is not a shift. Fitting a phase ramp
    over frequencies dominated by it would measure the colour, not the
    registration. Implemented in the frequency domain so the transfer function
    is exactly Gaussian and known."""
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    f2 = fy**2 + fx**2
    lp = np.exp(-2.0 * np.pi**2 * sigma**2 * f2)
    return np.real(np.fft.ifft2(np.fft.fft2(a) * (1.0 - lp)))


def shift_by(a, dy, dx):
    """Translate by an EXACT sub-pixel amount via a frequency-domain phase ramp.

    This is the positive-control stimulus. It is used rather than
    `scipy.ndimage.shift` because an interpolating shift applies its own
    kernel, so the planted displacement would be entangled with the
    interpolator's blur -- the same defect that made a truncated Gaussian an
    invalid sub-pixel blur stimulus earlier in this milestone. A pure phase
    ramp is an exact, information-preserving translation."""
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    ramp = np.exp(-2j * np.pi * (fy * dy + fx * dx))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * ramp))


def phase_ramp_shift(a, b, fmax=0.25, hp_sigma=4.0, wmin_frac=0.02):
    """Displacement `d` such that `b(x) ~= a(x - d)`. Returns `(dy, dx, rms)`.

    Positive `dy` means the content of `b` sits LOWER (larger y) than in `a`.

    `fmax` caps the fit to frequencies where a real optical system still has
    modulation; above it the cross-spectrum is noise and its phase is uniform.
    `wmin_frac` drops bins whose magnitude is a negligible fraction of the
    strongest, which are pure phase noise and would otherwise be fitted with
    weight proportional to nothing.
    """
    assert a.shape == b.shape
    h, w = a.shape
    win = hann2(h, w)
    af = np.fft.fft2(highpass(a.astype(np.float64), hp_sigma) * win)
    bf = np.fft.fft2(highpass(b.astype(np.float64), hp_sigma) * win)

    cps = np.conj(af) * bf
    fy = np.fft.fftfreq(h)[:, None] * np.ones((1, w))
    fx = np.fft.fftfreq(w)[None, :] * np.ones((h, 1))
    rad = np.sqrt(fy**2 + fx**2)

    mag = np.abs(cps)
    keep = (rad > 0) & (rad <= fmax) & (mag >= wmin_frac * mag.max())
    if keep.sum() < 32:
        return float("nan"), float("nan"), 0.0

    # Phase is only known mod 2*pi. For |d| well under one pixel the ramp does
    # not wrap within |f| <= fmax, so the raw angle is already unwrapped. The
    # returned residual is what says whether that assumption held.
    ph = np.angle(cps[keep])
    wgt = mag[keep]
    A = np.stack([fy[keep], fx[keep]], axis=1) * (-2.0 * np.pi)

    sw = np.sqrt(wgt)
    sol, *_ = np.linalg.lstsq(A * sw[:, None], ph * sw, rcond=None)
    dy, dx = float(sol[0]), float(sol[1])

    resid = ph - A @ sol
    rms = float(np.sqrt(np.average(resid**2, weights=wgt)))
    return dy, dx, rms


def load_tif(path):
    import tifffile

    return tifffile.imread(path)


def crop(img, y, x, s):
    return img[y : y + s, x : x + s]


def jdump(name, obj):
    os.makedirs(JSON, exist_ok=True)
    p = os.path.join(JSON, name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True, default=float)
    print("wrote %s" % p)
