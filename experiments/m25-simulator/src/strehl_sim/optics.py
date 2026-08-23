"""Optical transfer functions.

Two terms, multiplied in the frequency domain:

  * **diffraction**, the incoherent circular-aperture OTF at `N_eff`, which at
    this rig is *not* a small correction (fact 12: MTF@Nyquist is 0.000 at
    marked f/8 and f/11 once the bellows factor is applied);
  * **defocus**, the Fourier transform of a uniform disc of diameter `c`
    (the geometric circle of confusion).

Both are evaluated in **cycles per sensor pixel**, so a supersampled grid only
changes the frequency axis, never the physics.

Failure axes, stated here because this is where they enter:
  * no aberrations beyond diffraction (no coma, astigmatism, spherical);
  * defocus is a *uniform* disc, i.e. the exit pupil is taken as unobstructed
    and uniformly illuminated -- real bokeh has structure;
  * no longitudinal chromatic aberration unless `focus_shift` is passed;
  * the OTF is shift-invariant, so no field dependence.
"""

from __future__ import annotations

import numpy as np
from scipy.special import j1


def diffraction_otf(fr: np.ndarray, cutoff: float) -> np.ndarray:
    """Incoherent OTF of a circular aperture.

    `fr` is radial frequency in cycles/sensor-px; `cutoff` likewise.
    `H(v) = (2/pi) (acos v - v sqrt(1-v^2))`, zero past `v = 1`.
    """
    v = np.clip(fr / cutoff, 0.0, 1.0)
    h = (2.0 / np.pi) * (np.arccos(v) - v * np.sqrt(np.maximum(0.0, 1.0 - v * v)))
    return np.where(fr >= cutoff, 0.0, h)


def defocus_otf(fr: np.ndarray, coc_px: float) -> np.ndarray:
    """OTF of a uniform disc of diameter `coc_px` sensor px: `2 J1(x)/x`,
    `x = pi * coc * f`.  Negative lobes are real (contrast reversal) and are
    deliberately not clipped."""
    if coc_px <= 0.0:
        return np.ones_like(fr)
    x = np.pi * coc_px * fr
    out = np.ones_like(x)
    nz = x > 1e-12
    out[nz] = 2.0 * j1(x[nz]) / x[nz]
    return out


def radial_frequency_grid(shape, supersample: int) -> np.ndarray:
    """Radial spatial frequency in cycles per SENSOR pixel for an rfft2 grid.

    `shape` is the latent (supersampled) array shape.  One latent pixel is
    `1/supersample` of a sensor pixel, so a latent frequency of `f` cyc/latent
    px is `f * supersample` cyc/sensor px.
    """
    h, w = shape
    fy = np.fft.fftfreq(h)[:, None] * supersample
    fx = np.fft.rfftfreq(w)[None, :] * supersample
    return np.sqrt(fy * fy + fx * fx)


class OtfCache:
    """Caches the radial grid for one latent shape and builds per-(coc,lambda)
    transfer functions on demand."""

    def __init__(self, shape, supersample: int, pixel_pitch_um: float,
                 n_eff: float):
        self.shape = tuple(shape)
        self.supersample = supersample
        self.pitch = pixel_pitch_um
        self.n_eff = n_eff
        self._fr = radial_frequency_grid(shape, supersample)
        self._diff: dict[float, np.ndarray] = {}

    def cutoff(self, wavelength_nm: float) -> float:
        return self.pitch / (wavelength_nm * 1e-3 * self.n_eff)

    def diffraction(self, wavelength_nm: float) -> np.ndarray:
        key = round(float(wavelength_nm), 3)
        if key not in self._diff:
            self._diff[key] = diffraction_otf(self._fr, self.cutoff(key))
        return self._diff[key]

    def total(self, coc_px: float, wavelength_nm: float,
              with_diffraction: bool = True) -> np.ndarray:
        h = defocus_otf(self._fr, coc_px)
        if with_diffraction:
            h = h * self.diffraction(wavelength_nm)
        return h


def blur(img: np.ndarray, otf: np.ndarray) -> np.ndarray:
    """Circular convolution by an OTF.  The caller is responsible for enough
    margin that wrap-around never reaches the region it reads back."""
    return np.fft.irfft2(np.fft.rfft2(img) * otf, s=img.shape)


def mtf_at(cache: OtfCache, coc_px: float, wavelength_nm: float,
           f_cyc_per_px: float) -> float:
    """Scalar MTF at one frequency -- used by the self-tests to check the
    optics against fact 12's published MTF@Nyquist table."""
    fr = np.array([[f_cyc_per_px]])
    h = defocus_otf(fr, coc_px) * diffraction_otf(fr, cache.cutoff(wavelength_nm))
    return float(abs(h[0, 0]))
