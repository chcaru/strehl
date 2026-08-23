"""Scene builders matched to the corpus, and the fitted-vs-tested split.

**What is fitted and what is tested.**  Three scene nuisance parameters are
fitted from the real stack -- the mean green level, the texture contrast, and
the texture spectral slope.  They are radiometry and subject statistics, not
physics: no measurement in the fact table is a claim about them.  Everything
that Gate 1 tests -- the phi/excess coupling, the zero-centre-tap null, the
shape of the noise-versus-width curve, the mean's ratio, the placebo's ratio --
is left free.  `coc_px_per_frame` is **swept, not fitted**, in Gate 1a, so
that the mechanism claim cannot be tuned into existence.

The fit is done on frame `middle` of the real stack at the real ROI, and it
matches exactly two numbers (mean, sigma) plus one spectral slope.  Stating
that split is the whole point: a simulator that fits five numbers and then
"reproduces" five numbers has measured nothing.
"""

from __future__ import annotations

import numpy as np

from . import scene as SC
from .config import A7C2, Breathing, Capture, Optics
from .focus import NoiseModel
from .render import RenderConfig


def fit_radiometry(value_roi: np.ndarray, iso: float) -> tuple[float, float]:
    """Return `(base_e, contrast_e)` reproducing a real ROI's mean and sigma.

    The observed spatial variance is scene structure plus sensor noise; the
    noise part is known from the calibrated model, so the structure part is
    what is left.  DERIVED, and it is an *assumption* that the two add in
    quadrature -- true if structure and noise are independent, which they are
    by construction of the sensor model but not necessarily of the subject.
    """
    nm = NoiseModel.for_iso(iso)
    mean_dn = float(np.mean(value_roi))
    sd_dn = float(np.std(value_roi))
    noise_var = 0.5 * (nm.gain_dn_per_e * max(mean_dn, 0.0)
                       + (nm.read_noise_e * nm.gain_dn_per_e) ** 2)
    struct_var = sd_dn ** 2 - noise_var
    assert struct_var > 0, (
        f"ROI sigma {sd_dn:.3f} DN is below the model noise floor "
        f"{np.sqrt(noise_var):.3f} DN -- the noise model or the ROI is wrong")
    return mean_dn / nm.gain_dn_per_e, np.sqrt(struct_var) / nm.gain_dn_per_e


def fit_beta(value_roi: np.ndarray, lo=0.02, hi=0.20) -> float:
    """Least-squares slope of `log P(f)` against `log f` over a mid-band of the
    ROI's radially averaged power spectrum, in cycles per green-plane pixel.

    The band excludes the lowest frequencies (dominated by the ROI's own
    windowing) and the highest (dominated by sensor noise, which is white and
    would drag any slope toward zero).
    """
    a = np.asarray(value_roi, np.float64)
    a = a - a.mean()
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    p = np.abs(np.fft.rfft2(a * win)) ** 2
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.rfftfreq(a.shape[1])[None, :]
    fr = np.sqrt(fy * fy + fx * fx)
    m = (fr >= lo) & (fr <= hi)
    x = np.log(fr[m])
    y = np.log(np.maximum(p[m], 1e-30))
    slope = np.polyfit(x, y, 1)[0]
    return float(-slope)


def cfg_109(coc_px_per_frame: float, n_frames: int = 22, seed: int = 1,
            margin_px: int = 48, **kw) -> RenderConfig:
    """A render config matched to `109MSDCF`: ISO 160, marked f/11, 22 frames.

    Drift: fact 1 measured -1.012 % over 33 frames on 119MSDCF and -1.835 % on
    another stack, and stated that drift is NOT a low-order polynomial in
    frame index.  109MSDCF's own total is not published, so the default here
    is the 119MSDCF rate scaled to 22 frames, and it is a GENERATOR
    CONVENIENCE, not a model.  Callers who have a measured series should pass
    it in as `scale_series`.
    """
    return RenderConfig(
        sensor=A7C2,
        optics=Optics(n_marked=11.0, magnification=2.0, pupil_ratio=1.0),
        capture=Capture(iso=160.0, n_frames=n_frames,
                        coc_px_per_frame=coc_px_per_frame),
        breathing=Breathing(total_scale_change=-0.01012 * (n_frames - 1) / 32.0,
                            centre_x_px=-22.0, centre_y_px=-113.0),
        margin_px=margin_px, seed=seed, **kw)


def flat_scene(cfg: RenderConfig, sensor_hw, base_e, contrast_e, beta,
               focus_index=None, seed=0) -> SC.Scene:
    K = cfg.capture.n_frames
    u = (K - 1) / 2.0 if focus_index is None else focus_index
    return SC.flat_texture(sensor_hw, cfg_supersample(cfg), base_e,
                           contrast_e, u, beta=beta, seed=seed,
                           margin=cfg.margin_px)


def tilt_scene(cfg: RenderConfig, sensor_hw, base_e, contrast_e, beta,
               span_frames, seed=0) -> SC.Scene:
    K = cfg.capture.n_frames
    lo = (K - 1) / 2.0 - span_frames / 2.0
    hi = (K - 1) / 2.0 + span_frames / 2.0
    return SC.tilted_plane(sensor_hw, cfg_supersample(cfg), base_e,
                           contrast_e, lo, hi, beta=beta, seed=seed,
                           margin=cfg.margin_px)


_SS = {"value": 3}


def cfg_supersample(cfg: RenderConfig) -> int:
    return _SS["value"]


def set_supersample(s: int) -> None:
    _SS["value"] = int(s)
