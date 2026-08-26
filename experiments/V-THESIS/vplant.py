"""Exact plants for the V-THESIS instrument, and a symmetric despeckler.

gauss_exact  -- a TRUE Gaussian, applied in the Fourier domain. This exists
                because scipy.ndimage.gaussian_filter, at the sigmas that
                matter here, is not one: its kernel radius is
                int(truncate*sigma+0.5), so at sigma <= 0.12 it is bit-for-bit
                the identity and at sigma = 0.20 its MTF^2 at Nyquist is
                0.99997 against a true Gaussian's 0.674. A ladder built from it
                is flat over its first eight rungs, and anything inverted
                against that ladder inherits a ~0.2-0.4 px floor. Plants have to
                be exact or the control is not a control.

despeckle    -- replace pixels more than k sigma from their own 3x3 median with
                that median. Applied to BOTH arms identically, so it cannot
                favour either. It exists because isolated impulses put flat
                power into the spectrum that a median-based sigma estimator, by
                design, does not see -- and `argmax-baseline` produces impulses.
                The replaced fraction is returned so it can be checked rather
                than trusted.
"""
import numpy as np
from scipy.ndimage import median_filter


def gauss_exact(t, sigma):
    """True circular Gaussian blur via the exact transfer function."""
    if sigma <= 0:
        return np.array(t, dtype=np.float64)
    a = np.asarray(t, dtype=np.float64)
    n, m = a.shape
    F = np.fft.rfft2(a)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(m)[None, :]
    H = np.exp(-2.0 * np.pi ** 2 * sigma ** 2 * (fy * fy + fx * fx))
    return np.fft.irfft2(F * H, s=(n, m))


def scale_exact(t, out_n):
    """Resample to out_n x out_n by Fourier zero-pad / truncate.

    An ideal (sinc) resampler: it changes the sampling density and NOTHING
    else, so it can be used to build a scale mismatch with no blur in it.
    """
    a = np.asarray(t, dtype=np.float64)
    n = a.shape[0]
    F = np.fft.fftshift(np.fft.fft2(a))
    if out_n < n:
        c = n // 2
        h = out_n // 2
        G = F[c - h:c - h + out_n, c - h:c - h + out_n]
    else:
        G = np.zeros((out_n, out_n), dtype=complex)
        c = out_n // 2
        h = n // 2
        G[c - h:c - h + n, c - h:c - h + n] = F
    return np.fft.ifft2(np.fft.ifftshift(G)).real * (out_n / n) ** 2


def despeckle(t, sigma_dn, k=6.0):
    a = np.asarray(t, dtype=np.float64)
    med = median_filter(a, size=3, mode="nearest")
    bad = np.abs(a - med) > k * sigma_dn
    out = a.copy()
    out[bad] = med[bad]
    return out, float(bad.mean())
