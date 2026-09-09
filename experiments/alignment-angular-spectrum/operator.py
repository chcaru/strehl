"""Direct log-radius alignment prototype. No image-space refinement or hidden scale truth."""
import numpy as np
from scipy import fft, ndimage


def log_polar(image, radii, angles, floor_relative):
    """Sample log Fourier magnitude; radii are FFT-bin distances from DC."""
    image = np.asarray(image)
    radii = np.asarray(radii, dtype=np.float32)
    angles = np.asarray(angles, dtype=np.float32)
    if image.dtype != np.float32 or image.ndim != 2 or max(image.shape) > 512:
        raise ValueError("requires one f32 image no larger than 512x512")
    if not np.isfinite(image).all() or radii.ndim != 1 or angles.ndim != 1:
        raise ValueError("invalid image or sampling dimensions")
    if not np.isfinite(radii).all() or not np.isfinite(angles).all() or np.any(radii <= 0):
        raise ValueError("invalid polar coordinates")
    if not 0 < floor_relative < 1:
        raise ValueError("invalid fixed logarithm floor")
    spectrum = fft.fftshift(fft.fft2(image, workers=1))
    assert spectrum.dtype == np.complex64
    magnitude = np.abs(spectrum)
    peak = magnitude.max()
    if not peak > 0:
        raise ValueError("zero Fourier magnitude")
    logarithm = np.log(np.maximum(magnitude, np.float32(floor_relative)*peak))
    yy = np.float32(image.shape[0]//2) + radii[:, None]*np.sin(angles)[None, :]
    xx = np.float32(image.shape[1]//2) + radii[:, None]*np.cos(angles)[None, :]
    if yy.min() < 0 or xx.min() < 0 or yy.max() > image.shape[0]-1 or xx.max() > image.shape[1]-1:
        raise ValueError("polar support leaves the observed spectrum")
    sampled = ndimage.map_coordinates(logarithm, [yy, xx], order=1, mode="constant", cval=np.nan, prefilter=False)
    assert sampled.dtype == np.float32 and np.isfinite(sampled).all()
    return sampled


def descriptor(log_magnitude, centred):
    """Remove only the per-radius angular mean in the candidate arm."""
    values = np.asarray(log_magnitude)
    if values.dtype != np.float32 or values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("descriptor requires finite f32 log-polar samples")
    if centred:
        return values - values.mean(axis=1, keepdims=True, dtype=np.float32)
    return values.copy()


def scale_information(values, log_radius_step, margin):
    """Identifiability after the same offset/gain nuisance as spectral NCC."""
    core = values[margin:-margin]
    d = core - core.mean(dtype=np.float32)
    g = (values[margin+1:len(values)-margin+1] - values[margin-1:len(values)-margin-1]) / np.float32(2*log_radius_step)
    g = g - g.mean(dtype=np.float32)
    # Explicit f64 measurement reductions; descriptor and derivative arrays stay f32.
    energy = float(np.sum(d*d, dtype=np.float64))
    if not np.isfinite(energy) or energy <= 0:
        return dict(energy=energy, mean_energy=energy/d.size, information=0.0)
    gain = float(np.sum(g*d, dtype=np.float64))/energy
    perpendicular = g - np.float32(gain)*d
    information = float(np.sum(perpendicular*perpendicular, dtype=np.float64))/energy
    return dict(energy=energy, mean_energy=energy/d.size, information=information)


def estimate_scale(reference, moving, log_radius_step, max_shift,
                   min_scale_information=1e-3, min_peak_margin=1e-3, min_rms_energy=0.01):
    """Direct scale: moving(u)=reference(u+log(scale)); no later image-space fit."""
    reference = np.asarray(reference); moving = np.asarray(moving)
    if reference.shape != moving.shape or reference.ndim != 2 or reference.dtype != np.float32 or moving.dtype != np.float32:
        raise ValueError("matching finite f32 descriptor grids required")
    if max_shift < 2 or 2*max_shift+3 >= len(reference) or not log_radius_step > 0:
        raise ValueError("invalid fixed radial search support")
    result = dict(accepted=False, scale=None, log_scale=None, reason=None,
                  info_reference=None, info_moving=None, peak_score=None, peak_margin=None,
                  integer_shift=None, refined_shift=None)
    if not np.isfinite(reference).all() or not np.isfinite(moving).all():
        result["reason"] = "nonfinite"; return result
    ri = scale_information(reference, log_radius_step, max_shift)
    mi = scale_information(moving, log_radius_step, max_shift)
    result.update(info_reference=ri, info_moving=mi)
    if not np.isfinite(ri["information"]) or not np.isfinite(mi["information"]):
        result["reason"] = "nonfinite"; return result
    if ri["energy"] <= 0 or mi["energy"] <= 0:
        result["reason"] = "zero-energy"; return result
    if min(ri["mean_energy"], mi["mean_energy"]) < min_rms_energy*min_rms_energy:
        result["reason"] = "weak-energy"; return result
    if min(ri["information"], mi["information"]) < min_scale_information:
        result["reason"] = "scale-information"; return result
    core = reference[max_shift:-max_shift]
    fixed = core - core.mean(dtype=np.float32)
    fixed_power = float(np.sum(fixed*fixed, dtype=np.float64))
    scores = []
    shifts = list(range(-max_shift, max_shift+1))
    stop = len(reference)-max_shift
    for shift in shifts:
        sample = moving[max_shift+shift:stop+shift]
        sample = sample - sample.mean(dtype=np.float32)
        power = float(np.sum(sample*sample, dtype=np.float64))
        if power <= 0 or not np.isfinite(power):
            result["reason"] = "zero-energy"; return result
        scores.append(float(np.sum(fixed*sample, dtype=np.float64)) / (fixed_power*power)**0.5)
    if not np.isfinite(scores).all():
        result["reason"] = "nonfinite"; return result
    best = int(np.argmax(scores))
    result.update(peak_score=scores[best], integer_shift=shifts[best])
    if best == 0 or best == len(scores)-1:
        result["reason"] = "search-boundary"; return result
    competitors = [scores[0], scores[-1]] + [scores[i] for i in range(1, len(scores)-1)
        if i != best and scores[i] >= scores[i-1] and scores[i] >= scores[i+1]]
    margin = scores[best]-max(competitors)
    result["peak_margin"] = margin
    if margin < min_peak_margin:
        result["reason"] = "ambiguous-peak"; return result
    left, peak, right = scores[best-1:best+2]
    denominator = left-2*peak+right
    if not denominator < 0:
        result["reason"] = "invalid-parabola"; return result
    offset = 0.5*(left-right)/denominator
    if not np.isfinite(offset) or abs(offset) > 0.5:
        result["reason"] = "invalid-parabola"; return result
    refined = shifts[best]+offset
    log_scale = -refined*log_radius_step
    result.update(accepted=True, scale=float(np.exp(log_scale)), log_scale=log_scale,
                  reason=None, refined_shift=refined)
    return result
