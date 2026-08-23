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


def shaped_texture(shape, supersample, freq_green, amp_green,
                   rng: np.random.Generator) -> np.ndarray:
    """Zero-mean, unit-sd isotropic texture with a PRESCRIBED radial amplitude
    profile, given in **cycles per green-plane pixel**.

    `powerlaw_texture` assumes a single power law over the whole band.  M25's
    `10-spectrum-check.py` measured that this is a poor model for a real
    subject: `coffee-bean`'s green plane falls at f^-3.70 below 0.2 cyc/px and
    at f^-0.16 above it, so a single slope fitted on the low band starves the
    high band by 2x in power.  This lets the profile be *measured* instead.

    Frequency bookkeeping, stated because it is the easy thing to get wrong:
    the latent grid is `supersample` times finer than the CFA grid, and the
    green plane is 2x coarser than the CFA grid, so

        f_green [cyc / green px] = f_latent [cyc / latent px] * 2 * supersample

    and the profile is resampled onto the latent grid through that factor.
    Above the green Nyquist the profile is extrapolated flat, which matters
    only for content the sensor cannot represent anyway.
    """
    h, w = shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    fr = np.sqrt(fy * fy + fx * fx) * (2.0 * supersample)
    freq = np.asarray(freq_green, float)
    prof = np.asarray(amp_green, float)
    a = np.interp(fr, freq, prof, left=0.0, right=0.0)
    # Above the green Nyquist the profile says nothing.  Latent content there
    # is deliberately set to zero rather than extrapolated: a flat tail covers
    # ~97 % of the latent Fourier area at S=2, so unit-sd normalisation would
    # spend nearly all the variance on content the sensor cannot represent and
    # the delivered structure would collapse to the noise floor (measured:
    # `data/psd-shaping-check.txt`, first attempt).  The cost is that this path
    # under-models aliasing of super-Nyquist subject detail -- a stated axis.
    phase = rng.uniform(0.0, 2.0 * np.pi, size=fr.shape)
    spec = a * np.exp(1j * phase)
    spec[0, 0] = 0.0
    img = np.fft.irfft2(spec, s=(h, w))
    sd = img.std()
    return img / sd if sd > 0 else img


def _texture(shape, supersample, beta, rng, psd=None) -> np.ndarray:
    """One entry point so every scene family shapes its texture identically."""
    if psd is None:
        return powerlaw_texture(shape, beta, rng)
    return shaped_texture(shape, supersample, psd[0], psd[1], rng)


def _apply(base_e: float, texture: np.ndarray, contrast_e: float) -> np.ndarray:
    """Radiance in electrons: a positive mean plus a texture of given sd,
    floored at zero (a negative photon rate is meaningless)."""
    return np.maximum(0.0, base_e + contrast_e * texture)


# ---------------------------------------------------------------- scenes

def flat_texture(sensor_shape, supersample, base_e, contrast_e, focus_index,
                 beta=2.0, seed=0, name="flat", margin=0, psd=None) -> Scene:
    rng = np.random.default_rng(seed)
    hh, ww = sensor_shape[0] + 2 * margin, sensor_shape[1] + 2 * margin
    h, w = hh * supersample, ww * supersample
    t = _texture((h, w), supersample, beta, rng, psd)
    lay = Layer(_apply(base_e, t, contrast_e), np.ones((h, w), np.float32),
                float(focus_index), "plane")
    return Scene([lay], supersample, tuple(sensor_shape), name)


def tilted_plane(sensor_shape, supersample, base_e, contrast_e,
                 focus_lo, focus_hi, axis="x", beta=2.0, seed=0,
                 name="tilt", margin=0, psd=None) -> Scene:
    """Analytic linear depth: focus index ramps `focus_lo -> focus_hi` across
    the frame.  The cleanest available ground truth, and the matching null for
    occlusion work -- a plane has no occlusions, so any bimodality flagged on
    one is a false positive by construction (M21 §7)."""
    rng = np.random.default_rng(seed)
    hh, ww = sensor_shape[0] + 2 * margin, sensor_shape[1] + 2 * margin
    h, w = hh * supersample, ww * supersample
    t = _texture((h, w), supersample, beta, rng, psd)
    if axis == "x":
        ramp = np.linspace(focus_lo, focus_hi, w, dtype=np.float32)[None, :]
        ramp = np.repeat(ramp, h, axis=0)
    else:
        ramp = np.linspace(focus_lo, focus_hi, h, dtype=np.float32)[:, None]
        ramp = np.repeat(ramp, w, axis=1)
    lay = Layer(_apply(base_e, t, contrast_e), np.ones((h, w), np.float32),
                ramp, "plane")
    return Scene([lay], supersample, tuple(sensor_shape), name)


def _disc_field(h, w, supersample, frac, rng, r_min=None, r_max=None,
                exponent=None):
    """Signed distance to the union of a random field of discs.

    One occluding edge in a frame is not enough for M21's binning, which needs
    >= 500 pixels in each of the depth-step and smooth-depth bins.  A disc
    field gives O(10^4) pixels of boundary while keeping the geometry simple
    enough to reason about.  `frac` sets the areal coverage target.

    Default: single-scale, radius 55 latent px with +/-40 % jitter.  Passing
    `r_min`/`r_max`/`exponent` instead draws radii from a power law
    `N(r) ~ r^-exponent` over `[r_min, r_max]` **in latent px**, which is the
    multi-scale variant of section 11.  `exponent = 3` gives equal occluded
    area per octave of radius.
    """
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    d = np.full((h, w), -1e9, np.float32)

    if exponent is None:
        radii = []
        r_px = 55.0 * supersample
        n = max(1, int(round(frac * h * w / (np.pi * r_px ** 2))))
        radii = [r_px * rng.uniform(0.6, 1.4) for _ in range(n)]
    else:
        # Inverse-transform sample N(r) ~ r^-exponent, then keep drawing until
        # the *cumulative disc area* reaches the coverage target.  Area, not
        # count, is the thing being held fixed against the control.
        lo, hi = float(r_min), float(r_max)
        a = 1.0 - exponent
        target = frac * h * w
        radii, acc = [], 0.0
        while acc < target and len(radii) < 200000:
            u = rng.random()
            r = (lo ** a + u * (hi ** a - lo ** a)) ** (1.0 / a)
            radii.append(r)
            acc += np.pi * r * r

    for r in radii:
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        # Bounding box only.  A power-law size distribution puts O(10^4) small
        # discs on the grid, and touching the whole array for each is
        # quadratic enough to look like a hang: see section 11.6.
        y0 = max(int(cy - r) - 1, 0)
        y1 = min(int(cy + r) + 2, h)
        x0 = max(int(cx - r) - 1, 0)
        x1 = min(int(cx + r) + 2, w)
        if y0 >= y1 or x0 >= x1:
            continue
        sub = d[y0:y1, x0:x1]
        dy = yy[y0:y1, 0:1] - cy
        dx = xx[0:1, x0:x1] - cx
        np.maximum(sub, r - np.sqrt(dy * dy + dx * dx), out=sub)
    return d


def _fractal_field(h, w, frac, beta_mask, rng):
    """Approximate signed distance to the level set of an `f^-beta` field.

    A thresholded isotropic Gaussian random field has occluding structure at
    **every** scale, which is the property section 11 is testing and which a
    disc field of one radius does not have.  The threshold is set by quantile
    so that areal coverage matches the disc control.

    The raw field value is not a distance, so it is divided by the RMS gradient
    magnitude of the field.  That makes the level set's transition ~1 latent
    px on average, matching the anti-aliasing convention used by every other
    occluder here, instead of a width that drifts with `beta_mask`.
    """
    t = powerlaw_texture((h, w), beta_mask, rng)
    thr = float(np.quantile(t, 1.0 - frac))
    gy, gx = np.gradient(t)
    g = float(np.sqrt((gy * gy + gx * gx).mean()))
    return ((t - thr) / max(g, 1e-9)).astype(np.float32)


def stepped_plane(sensor_shape, supersample, base_e, contrast_e,
                  near_focus, far_focus, edge_frac=0.35, beta=2.0, seed=0,
                  name="terrace", margin=0, psd=None) -> Scene:
    """A SINGLE opaque layer with a piecewise-constant focus map.

    This is the control M21 could not build on real data: the same depth steps
    as the occlusion scene, but **no alpha boundary and therefore no veiling**
    -- a terraced surface seen head-on rather than one object in front of
    another.  If multi-peak enrichment survives here at full strength, the
    enrichment is about depth discontinuity per se; if it collapses, it is
    about occlusion.  Either answer is worth having.
    """
    rng = np.random.default_rng(seed)
    hh, ww = sensor_shape[0] + 2 * margin, sensor_shape[1] + 2 * margin
    h, w = hh * supersample, ww * supersample
    d = _disc_field(h, w, supersample, edge_frac, rng)
    m = (d > 0).astype(np.float32)
    focus = (far_focus + (near_focus - far_focus) * m).astype(np.float32)
    t = _texture((h, w), supersample, beta, rng, psd)
    lay = Layer(_apply(base_e, t, contrast_e), np.ones((h, w), np.float32),
                focus, "terrace")
    return Scene([lay], supersample, tuple(sensor_shape), name)


def flatten_scene(sc: Scene, name="flattened") -> Scene:
    """Collapse a multi-layer scene into ONE opaque layer carrying the
    geometric composite radiance and the geometrically visible focus map.

    Rendering *this* is the wrong physics -- it is composite-then-blur, the
    "layered blur" shortcut.  It exists only as a negative control: a
    background pixel behind a blurred occluder becomes a blur of an
    already-occluded image instead of a veiled view of the background.  Never
    call it from the forward model.
    """
    h, w = sc.layers[0].radiance.shape[:2]
    focus = np.zeros((h, w), np.float32)
    rad = np.zeros((h, w), np.float32)
    for lay in sc.layers:                                    # far -> near
        a = np.clip(lay.alpha, 0.0, 1.0)
        f = (np.full((h, w), float(lay.focus), np.float32)
             if np.ndim(lay.focus) == 0 else lay.focus)
        focus = a * f + (1 - a) * focus
        rad = a * lay.radiance + (1 - a) * rad
    lay = Layer(rad, np.ones((h, w), np.float32), focus, "flattened")
    return Scene([lay], sc.supersample, sc.sensor_shape, name)


def two_layer_occlusion(sensor_shape, supersample, bg_e, bg_contrast_e,
                        fg_e, fg_contrast_e, bg_focus, fg_focus,
                        shape="halfplane", edge_frac=0.5, beta=2.0,
                        seed=0, name="occlusion", margin=0, psd=None,
                        mask_beta=2.6, mask_r=(2.0, 160.0),
                        mask_exponent=3.0) -> Scene:
    """A foreground object at one depth partially covering a background at
    another, with a genuine alpha boundary.

    `shape`:
      * `halfplane`      -- a straight vertical boundary at `edge_frac` of W;
      * `disc`           -- a centred disc of radius `edge_frac*min(H,W)/2`;
      * `bar`            -- a vertical bar of width `edge_frac * W` centred;
      * `discs`          -- a field of ~55 latent-px discs (SINGLE SCALE);
      * `discs-powerlaw` -- a disc field with radii ~ `r^-mask_exponent` over
                            `mask_r` latent px (MULTI-SCALE, section 11);
      * `fractal`        -- a thresholded `f^-mask_beta` field (MULTI-SCALE,
                            structure at every scale, section 11).

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
    elif shape == "discs":
        d = _disc_field(h, w, supersample, edge_frac, rng)
    elif shape == "discs-powerlaw":
        d = _disc_field(h, w, supersample, edge_frac, rng,
                        r_min=mask_r[0], r_max=mask_r[1],
                        exponent=mask_exponent)
    elif shape == "fractal":
        d = _fractal_field(h, w, edge_frac, mask_beta, rng)
    else:
        raise ValueError(f"unknown occluder shape {shape!r}")
    alpha = np.clip(d + 0.5, 0.0, 1.0).astype(np.float32)

    tb = _texture((h, w), supersample, beta, rng, psd)
    tf = _texture((h, w), supersample, beta, rng, psd)
    bg = Layer(_apply(bg_e, tb, bg_contrast_e), np.ones((h, w), np.float32),
               float(bg_focus), "background")
    fg = Layer(_apply(fg_e, tf, fg_contrast_e), alpha, float(fg_focus),
               "foreground")
    return Scene([bg, fg], supersample, tuple(sensor_shape), name)
