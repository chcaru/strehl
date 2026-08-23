"""Latent scenes.

A scene is a **list of layers**, ordered far to near.  Each layer carries

  * `radiance`  -- (H, W) or (H, W, 3), in electrons per sensor pixel per
                   frame at unit photometric gain, on the supersampled grid;
  * `alpha`     -- (H, W) coverage in [0, 1], with a genuine sub-sensor-pixel
                   boundary;
  * `focus`     -- scalar or (H, W): the (possibly fractional) frame index at
                   which that point is exactly in focus.  This is the depth
                   map, expressed in the one currency this project can
                   actually measure (fact 54's "focus index").

Everything is defined on a grid `supersample` times finer than the sensor, so
sampling is modelled rather than assumed.

Three scene families, as required:

  * `flat_texture`        -- fronto-parallel textured plane.  Legitimate for
                             noise-coupling work; **illegitimate for any
                             spatial-support sweep** (facts 61/62: a
                             fronto-parallel plant cannot turn over).
  * `tilted_plane`        -- analytic linear depth, the cleanest ground truth.
  * `two_layer_occlusion` -- a foreground object with a real alpha boundary
                             partially covering a background at another depth.
                             This is the one M21 needs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Layer:
    radiance: np.ndarray          # (H, W) or (H, W, 3), electrons
    alpha: np.ndarray             # (H, W)
    focus: np.ndarray | float     # scalar or (H, W), in frame-index units
    name: str = ""


@dataclass
class Scene:
    layers: list[Layer]           # far to near
    supersample: int
    sensor_shape: tuple[int, int]  # (H, W) in sensor px
    name: str = ""

    @property
    def latent_shape(self) -> tuple[int, int]:
        return (self.sensor_shape[0] * self.supersample,
                self.sensor_shape[1] * self.supersample)


# --------------------------------------------------------------- texture

def powerlaw_texture(shape, beta: float, rng: np.random.Generator,
                     f_lo: float = 0.0) -> np.ndarray:
    """Zero-mean, unit-sd, band-limited isotropic texture with power spectral
    density `~ f^-beta`.

    Generated in the Fourier domain, so it is band-limited to the latent
    Nyquist **by construction** and the supersampled grid carries no aliasing
    of its own.  `beta = 2` is a reasonable stand-in for natural-image
    statistics; the real texture statistics of insects and organic subjects are
    a stated failure axis.
    """
    h, w = shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    fr = np.sqrt(fy * fy + fx * fx)
    amp = np.zeros_like(fr)
    ok = fr > max(f_lo, 1e-9)
    amp[ok] = fr[ok] ** (-beta / 2.0)
    phase = rng.uniform(0.0, 2.0 * np.pi, size=fr.shape)
    spec = amp * np.exp(1j * phase)
    spec[0, 0] = 0.0
    img = np.fft.irfft2(spec, s=(h, w))
    sd = img.std()
    return img / sd if sd > 0 else img


def _apply(base_e: float, texture: np.ndarray, contrast_e: float) -> np.ndarray:
    """Radiance in electrons: a positive mean plus a texture of given sd,
    floored at zero (a negative photon rate is meaningless)."""
    return np.maximum(0.0, base_e + contrast_e * texture)


# ---------------------------------------------------------------- scenes

def flat_texture(sensor_shape, supersample, base_e, contrast_e, focus_index,
                 beta=2.0, seed=0, name="flat", margin=0) -> Scene:
    rng = np.random.default_rng(seed)
    hh, ww = sensor_shape[0] + 2 * margin, sensor_shape[1] + 2 * margin
    h, w = hh * supersample, ww * supersample
    t = powerlaw_texture((h, w), beta, rng)
    lay = Layer(_apply(base_e, t, contrast_e), np.ones((h, w), np.float32),
                float(focus_index), "plane")
    return Scene([lay], supersample, tuple(sensor_shape), name)


def tilted_plane(sensor_shape, supersample, base_e, contrast_e,
                 focus_lo, focus_hi, axis="x", beta=2.0, seed=0,
                 name="tilt", margin=0) -> Scene:
    """Analytic linear depth: focus index ramps `focus_lo -> focus_hi` across
    the frame.  The cleanest available ground truth, and the matching null for
    occlusion work -- a plane has no occlusions, so any bimodality flagged on
    one is a false positive by construction (M21 §7)."""
    rng = np.random.default_rng(seed)
    hh, ww = sensor_shape[0] + 2 * margin, sensor_shape[1] + 2 * margin
    h, w = hh * supersample, ww * supersample
    t = powerlaw_texture((h, w), beta, rng)
    if axis == "x":
        ramp = np.linspace(focus_lo, focus_hi, w, dtype=np.float32)[None, :]
        ramp = np.repeat(ramp, h, axis=0)
    else:
        ramp = np.linspace(focus_lo, focus_hi, h, dtype=np.float32)[:, None]
        ramp = np.repeat(ramp, w, axis=1)
    lay = Layer(_apply(base_e, t, contrast_e), np.ones((h, w), np.float32),
                ramp, "plane")
    return Scene([lay], supersample, tuple(sensor_shape), name)


def two_layer_occlusion(sensor_shape, supersample, bg_e, bg_contrast_e,
                        fg_e, fg_contrast_e, bg_focus, fg_focus,
                        shape="halfplane", edge_frac=0.5, beta=2.0,
                        seed=0, name="occlusion", margin=0) -> Scene:
    """A foreground object at one depth partially covering a background at
    another, with a genuine alpha boundary.

    `shape`:
      * `halfplane` -- a straight vertical boundary at `edge_frac` of the width;
      * `disc`      -- a centred disc of radius `edge_frac * min(H, W) / 2`;
      * `bar`       -- a vertical bar of width `edge_frac * W` centred.

    The alpha boundary is anti-aliased over ONE LATENT pixel, i.e. `1 /
    supersample` of a sensor pixel, so the boundary is genuinely sub-pixel and
    the sampling of it is modelled rather than assumed.
    """
    rng = np.random.default_rng(seed)
    hh, ww = sensor_shape[0] + 2 * margin, sensor_shape[1] + 2 * margin
    h, w = hh * supersample, ww * supersample
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    if shape == "halfplane":
        d = xx - edge_frac * w                       # >0 inside the foreground
    elif shape == "disc":
        r = edge_frac * min(h, w) / 2.0
        d = r - np.sqrt((xx - w / 2.0) ** 2 + (yy - h / 2.0) ** 2)
    elif shape == "bar":
        half = edge_frac * w / 2.0
        d = half - np.abs(xx - w / 2.0)
    else:
        raise ValueError(f"unknown occluder shape {shape!r}")
    alpha = np.clip(d + 0.5, 0.0, 1.0).astype(np.float32)

    tb = powerlaw_texture((h, w), beta, rng)
    tf = powerlaw_texture((h, w), beta, rng)
    bg = Layer(_apply(bg_e, tb, bg_contrast_e), np.ones((h, w), np.float32),
               float(bg_focus), "background")
    fg = Layer(_apply(fg_e, tf, fg_contrast_e), alpha, float(fg_focus),
               "foreground")
    return Scene([bg, fg], supersample, tuple(sensor_shape), name)
