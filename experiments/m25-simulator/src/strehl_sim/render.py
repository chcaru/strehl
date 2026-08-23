"""The forward model.

For frame `k`, in this order:

  1. **geometry** -- warp every layer's radiance, alpha and focus map by the
     4-parameter similarity `s_k` about a per-stack centre (focus breathing:
     a magnification change about a near-fixed centre, NOT parallax).
     Geometry precedes the optical blur because the image is *formed* and
     then blurred by the aperture at that focus setting.
  2. **defocus + diffraction, per layer** -- each layer gets its OWN
     depth-dependent PSF, composed with the diffraction PSF at `N_eff`.
  3. **composite, back to front, in premultiplied alpha** --

         acc <- C_l + (1 - A_l) * acc
         C_l = (L_l * alpha_l) (x) PSF_l ,   A_l = alpha_l (x) PSF_l

     Each layer is blurred by its own PSF and **alpha is blurred too**, then
     composited.  Blurring *after* compositing is the wrong order: it makes a
     background pixel behind a blurred occluder a blur of an already-occluded
     image rather than a veiled view of the background, which is precisely the
     effect M21 exists to study.  This simulator does the physical order.
  4. **photometric gain** `g_k` (default 1.0) -- fact 180/181: per-frame level
     varies 0.91-11.70 % peak-to-peak across the corpus and EXIF does not
     predict it.
  5. **pixel aperture + CFA sampling** -- box-integrate `S x S` latent samples
     per photosite, then keep one colour per photosite (see `sensor.py`).
  6. **noise** -- Poisson shot + Gaussian read in electrons, then `g`, black
     level, DSNU and hot pixels, clipped at the usable white level.

Ground truth emitted alongside: the latent radiance, the focus-index map, the
per-frame focus plane, warp parameters, gain, and the per-pixel index of the
truly best-focused frame.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from . import optics as opt
from .config import LAMBDA_NM, Breathing, Capture, Optics, Sensor
from .scene import Layer, Scene
from .sensor import FixedPattern, expose, mosaic, pixel_aperture_integrate

CHANNELS = ("R", "G", "B")


@dataclass
class RenderConfig:
    sensor: Sensor
    optics: Optics
    capture: Capture
    breathing: Breathing
    margin_px: int = 48                 # sensor px of guard band on each side
    seed: int = 1
    fixed_seed: int = 12345
    with_diffraction: bool = True       # Gate 2 knob
    gain_dn_per_e: float | None = None  # Gate 2 knob
    shot: bool = True
    read: bool = True
    fpn: bool = True
    channel_scale: tuple = (0.55, 1.0, 0.42)   # relative WB-ish channel gains
    chromatic_diffraction: bool = True
    depth_bands: int = 12               # for layers with a spatially varying
                                        # focus map; ignored for scalar focus
    resampler_order: int = 3            # discipline 11: state the resampler


@dataclass
class Stack:
    frames: np.ndarray                  # (K, H, W) uint16 CFA
    focus_planes: np.ndarray            # (K,) frame focus index (== arange)
    scale: np.ndarray                   # (K,) per-frame similarity scale
    gain: np.ndarray                    # (K,) per-frame photometric gain
    truth: dict = field(default_factory=dict)


# --------------------------------------------------------------------- warp

def similarity_warp(img: np.ndarray, scale: float, cx: float, cy: float,
                    tx: float, ty: float, theta: float, order: int) -> np.ndarray:
    """Resample `img` under `x_dst = c + s R (x_src - c) + t`.

    Inverse mapping, cubic spline by default.  `mode='nearest'` at the border
    is safe because the caller always keeps a margin larger than the total
    displacement.
    """
    if scale == 1.0 and tx == 0.0 and ty == 0.0 and theta == 0.0:
        return img
    h, w = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    dx = xx - cx - tx
    dy = yy - cy - ty
    if theta != 0.0:
        c, s = np.cos(-theta), np.sin(-theta)
        rx, ry = c * dx - s * dy, s * dx + c * dy
    else:
        rx, ry = dx, dy
    src_x = cx + rx / scale
    src_y = cy + ry / scale
    return ndimage.map_coordinates(img, [src_y, src_x], order=order,
                                   mode="nearest")


# ------------------------------------------------------------------- layers

def _layer_terms(layer: Layer, k: float, cache: opt.OtfCache,
                 coc_per_frame: float, lam_nm: float, cfg: RenderConfig,
                 radiance: np.ndarray, alpha: np.ndarray,
                 focus: np.ndarray | float):
    """Return `(C, A)`: premultiplied blurred colour and blurred coverage for
    one layer at one frame, at one wavelength.

    Scalar focus is exact.  A spatially varying focus map is handled by a
    depth-banded decomposition with tent weights and an explicit
    band-partition normaliser `W`, so that `alpha == 1` gives `A == 1`
    exactly and the scalar case is recovered when there is one band.  The
    decomposition ignores *within-layer* self-occlusion -- a stated
    approximation.
    """
    if np.isscalar(focus) or np.ndim(focus) == 0:
        coc = abs(k - float(focus)) * coc_per_frame
        h = cache.total(coc, lam_nm, cfg.with_diffraction)
        return opt.blur(radiance * alpha, h), opt.blur(alpha, h)

    lo, hi = float(np.min(focus)), float(np.max(focus))
    nb = 1 if hi - lo < 1e-6 else int(cfg.depth_bands)
    if nb == 1:
        coc = abs(k - 0.5 * (lo + hi)) * coc_per_frame
        h = cache.total(coc, lam_nm, cfg.with_diffraction)
        return opt.blur(radiance * alpha, h), opt.blur(alpha, h)

    centres = np.linspace(lo, hi, nb)
    step = centres[1] - centres[0]
    Cn = np.zeros_like(radiance)
    An = np.zeros_like(radiance)
    Wn = np.zeros_like(radiance)
    for c in centres:
        w = np.clip(1.0 - np.abs(focus - c) / step, 0.0, 1.0)
        if not np.any(w > 0):
            continue
        h = cache.total(abs(k - c) * coc_per_frame, lam_nm, cfg.with_diffraction)
        Cn += opt.blur(radiance * alpha * w, h)
        An += opt.blur(alpha * w, h)
        Wn += opt.blur(w, h)
    Wn = np.maximum(Wn, 1e-6)
    return Cn / Wn, An / Wn


# ------------------------------------------------------------------- render

def render_stack(sc: Scene, cfg: RenderConfig,
                 scale_series: np.ndarray | None = None,
                 gain_series: np.ndarray | None = None,
                 focus_planes: np.ndarray | None = None,
                 progress: bool = False) -> Stack:
    """Render a focus bracket.

    `scale_series` is the per-frame similarity scale, supplied EXPLICITLY.
    Fact 1's supersession is binding: inter-frame drift is not well modelled
    by a low-order polynomial in frame index, so the simulator never models it
    -- it takes the series as ground truth.  The linear default is a generator
    convenience and is labelled as such in the report.
    """
    K = cfg.capture.n_frames
    if focus_planes is None:
        focus_planes = np.arange(K, dtype=np.float64)
    assert len(focus_planes) == K

    if scale_series is None:
        t = np.linspace(0.0, 1.0, K)
        scale_series = 1.0 + cfg.breathing.total_scale_change * t
    scale_series = np.asarray(scale_series, dtype=np.float64)
    assert scale_series.shape == (K,)

    if gain_series is None:
        if cfg.capture.gain_pp > 0:
            rg = np.random.default_rng(cfg.seed + 7717)
            walk = np.cumsum(rg.normal(0.0, 1.0, K))
            walk -= walk.mean()
            span = walk.max() - walk.min()
            walk = walk / span if span > 0 else walk
            gain_series = 1.0 + cfg.capture.gain_pp * walk
        else:
            gain_series = np.ones(K)
    gain_series = np.asarray(gain_series, dtype=np.float64)
    assert gain_series.shape == (K,)

    S = sc.supersample
    Hs, Ws = sc.sensor_shape
    m = cfg.margin_px
    # Scene arrays are expected to already include the margin.
    exp_h, exp_w = (Hs + 2 * m) * S, (Ws + 2 * m) * S
    for lay in sc.layers:
        assert lay.radiance.shape[:2] == (exp_h, exp_w), (
            f"layer {lay.name!r} is {lay.radiance.shape[:2]}, expected "
            f"{(exp_h, exp_w)}: build scenes with sensor_shape="
            f"{(Hs + 2 * m, Ws + 2 * m)}")

    cache = opt.OtfCache((exp_h, exp_w), S, cfg.sensor.pixel_pitch_um,
                         cfg.optics.n_eff)
    cx = exp_w / 2.0 + cfg.breathing.centre_x_px * S
    cy = exp_h / 2.0 + cfg.breathing.centre_y_px * S

    rng = np.random.default_rng(cfg.seed)
    fixed = FixedPattern((Hs, Ws), cfg.capture.iso, cfg.sensor,
                         seed=cfg.fixed_seed) if cfg.fpn else None

    frames = np.empty((K, Hs, Ws), dtype=np.uint16)
    y0, y1 = m * S, (m + Hs) * S
    x0, x1 = m * S, (m + Ws) * S

    for k in range(K):
        s = scale_series[k]
        tx = cfg.breathing.tx_px * S
        ty = cfg.breathing.ty_px * S
        warped = []
        for lay in sc.layers:
            rad = similarity_warp(lay.radiance, s, cx, cy, tx, ty,
                                  cfg.breathing.rotation_rad,
                                  cfg.resampler_order)
            alp = similarity_warp(lay.alpha, s, cx, cy, tx, ty,
                                  cfg.breathing.rotation_rad,
                                  cfg.resampler_order)
            alp = np.clip(alp, 0.0, 1.0)
            if np.ndim(lay.focus) == 0:
                foc = float(lay.focus)
            else:
                foc = similarity_warp(lay.focus, s, cx, cy, tx, ty,
                                      cfg.breathing.rotation_rad, 1)
            warped.append((rad, alp, foc))

        chans = np.empty((Hs, Ws, 3), dtype=np.float64)
        for ci, cname in enumerate(CHANNELS):
            lam = (LAMBDA_NM[cname] if cfg.chromatic_diffraction
                   else LAMBDA_NM["G"])
            acc = np.zeros((exp_h, exp_w), dtype=np.float64)
            for (rad, alp, foc) in warped:                 # far -> near
                C, A = _layer_terms(None, focus_planes[k], cache,
                                    cfg.capture.coc_px_per_frame, lam, cfg,
                                    rad * cfg.channel_scale[ci], alp, foc)
                acc = C + (1.0 - np.clip(A, 0.0, 1.0)) * acc
            acc = acc[y0:y1, x0:x1] * gain_series[k]
            chans[:, :, ci] = pixel_aperture_integrate(acc, S)

        e = mosaic(chans)
        frames[k] = expose(e, cfg.capture.iso, cfg.sensor, fixed, rng,
                           shot=cfg.shot, read=cfg.read,
                           gain_dn_per_e=cfg.gain_dn_per_e)
        if progress:
            print(f"  frame {k + 1}/{K}", flush=True)

    truth = ground_truth(sc, cfg, focus_planes)
    truth["fixed_pattern_sigma_dn"] = (fixed.sigma_fpn_dn if fixed else 0.0)
    truth["n_hot"] = (fixed.n_hot if fixed else 0)
    return Stack(frames, np.asarray(focus_planes), scale_series, gain_series,
                 truth)


def ground_truth(sc: Scene, cfg: RenderConfig,
                 focus_planes: np.ndarray) -> dict:
    """Per-sensor-pixel truth at frame 0's geometry (the reference frame).

    `visible_focus` composites the layers' focus maps under *geometric*
    (unblurred) alpha, i.e. what a hypothetical infinitely sharp camera would
    see.  `best_frame` is the frame whose focus plane is nearest to it.
    `alpha_fg` is the geometric coverage of the nearest layer, which is what a
    reconstruction of an occluded background has to beat.
    """
    S = sc.supersample
    Hs, Ws = sc.sensor_shape
    m = cfg.margin_px
    y0, y1 = m * S, (m + Hs) * S
    x0, x1 = m * S, (m + Ws) * S

    h, w = sc.layers[0].radiance.shape[:2]
    focus = np.zeros((h, w))
    rad = np.zeros((h, w))
    cov = np.zeros((h, w))
    for lay in sc.layers:                                   # far -> near
        a = np.clip(lay.alpha, 0.0, 1.0)
        f = (np.full((h, w), float(lay.focus)) if np.ndim(lay.focus) == 0
             else lay.focus)
        focus = a * f + (1 - a) * focus
        rad = a * lay.radiance + (1 - a) * rad
        cov = a + (1 - a) * cov

    def crop_to_sensor(x):
        return pixel_aperture_integrate(x[y0:y1, x0:x1], S)

    vf = crop_to_sensor(focus)
    fp = np.asarray(focus_planes)
    best = np.argmin(np.abs(vf[..., None] - fp[None, None, :]), axis=-1)
    return {
        "latent_radiance": rad[y0:y1, x0:x1].astype(np.float32),
        "latent_focus": focus[y0:y1, x0:x1].astype(np.float32),
        "visible_focus": vf.astype(np.float32),
        "best_frame": best.astype(np.int16),
        "alpha_front": crop_to_sensor(
            np.clip(sc.layers[-1].alpha, 0, 1)).astype(np.float32),
        "sensor_radiance": crop_to_sensor(rad).astype(np.float32),
        "n_layers": len(sc.layers),
        "supersample": S,
        "n_eff": cfg.optics.n_eff,
        "coc_px_per_frame": cfg.capture.coc_px_per_frame,
        "iso": cfg.capture.iso,
    }
