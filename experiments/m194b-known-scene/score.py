"""M194b fixed-target error readout; no M25/production implementation imports.

MSE may reward loss of texture when noise falls. Named wave response discloses
that tradeoff. Temporal variance is across repeats, never across scene pixels.
This is a synthetic software benchmark, not a physical-reference/SOTA score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


PLANE_WAVES = ((1800.0, 1 / 16, 1 / 24, 0.2),
               (900.0, 1 / 8, -1 / 16, 1.1))
COLOR_WAVES = ((450.0, 0.08, 0.03, 0.2),
               (180.0, 0.19, -0.07, 1.1),
               (240.0, 0.11, 0.04, 0.8),
               (120.0, 0.05, -0.09, 2.0))
CHANNEL_SCALE = np.array([0.75, 1.0, 0.60], dtype=np.float64)
WB = np.array([4 / 3, 1.0, 5 / 3], dtype=np.float32).astype(np.float64)
BLACK, WHITE, GAIN = 512, 15360, 0.25
CAMERA_LINEAR_DESCRIPTION = (
    "Linear camera-native RGB (sensor primaries), NO colour matrix, no transfer curve. "
    "THIS IS NOT sRGB -- do not treat it as such. This is the measurement output. "
    "White balance: as-shot per-channel gains, green = 1, applied AFTER black "
    "subtraction and normalisation by (white - black), and AFTER the noise model, "
    "which is calibrated in raw DN before any gain."
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def array_hash(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def finite_array(value, name: str) -> np.ndarray:
    a = np.asarray(value, dtype=np.float64)
    if not a.size or not np.isfinite(a).all():
        raise ValueError(f"{name}: empty or nonfinite")
    return a


def aperture(fx: float, fy: float, subsamples: int | None = None) -> float:
    """Unit native-pixel box, continuous or exact finite midpoint quadrature."""
    if subsamples is None:
        return float(np.sinc(fx) * np.sinc(fy))
    if isinstance(subsamples, bool) or not isinstance(subsamples, int) or subsamples < 1:
        raise ValueError("subsamples must be a positive integer")
    offsets = (np.arange(subsamples, dtype=np.float64) + 0.5) / subsamples - 0.5
    return float(np.cos(2 * np.pi * fx * offsets).mean()
                 * np.cos(2 * np.pi * fy * offsets).mean())


def diffraction(fx: float, fy: float, pitch_um=5.12,
                wavelength_nm=535.0, n_eff=16.0) -> float:
    """DERIVED normalized overlap of two circular pupils; explicit model only."""
    if min(pitch_um, wavelength_nm, n_eff) <= 0:
        raise ValueError("invalid optical constants")
    cutoff = pitch_um / (wavelength_nm * 1e-3 * n_eff)
    rho = math.hypot(fx, fy) / cutoff
    if rho >= 1:
        return 0.0
    return 2 / math.pi * (math.acos(rho) - rho * math.sqrt(1 - rho * rho))


def canonical_grid(width: int, height: int, crop_x=0, crop_y=0):
    vals = (width, height, crop_x, crop_y)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in vals):
        raise ValueError("integer output geometry required")
    if min(width, height) <= 0 or min(crop_x, crop_y) < 0:
        raise ValueError("invalid output geometry")
    y, x = np.indices((height, width), dtype=np.float64)
    return x + 2 * crop_x, y + 2 * crop_y


def main_mask(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    if x.shape != y.shape:
        raise ValueError("coordinate shape mismatch")
    mask = (x >= 64) & (x < 256) & (y >= 64) & (y < 176)
    if int(mask.sum()) != 192 * 112:
        raise ValueError("fixed canonical score window did not survive crop")
    return mask


def target(scene: str, x, y, kind="ideal", subsamples=4) -> np.ndarray:
    """Fixed desired WB-normalized DN; no output-derived normalization."""
    x, y = finite_array(x, "x"), finite_array(y, "y")
    if x.shape != y.shape or x.ndim != 2:
        raise ValueError("target expects matching two-dimensional coordinates")
    if kind not in ("ideal", "observation"):
        raise ValueError("unknown target convention")
    if scene in ("flat", "plane"):
        radiance = np.full_like(x, 12000.0)
        if scene == "plane":
            for amp, fx, fy, phase in PLANE_WAVES:
                transfer = aperture(fx, fy, subsamples if kind == "observation" else None)
                if kind == "observation":
                    transfer *= diffraction(fx, fy)
                radiance += amp * transfer * np.cos(2 * np.pi * (fx * x + fy * y) + phase)
        return radiance[..., None] * GAIN * (CHANNEL_SCALE * WB)
    if scene in ("color", "color-null", "achromatic"):
        if kind != "ideal":
            raise ValueError("analytic color has no optical observation claim")
        waves = [amp * aperture(fx, fy) * np.cos(2 * np.pi * (fx * x + fy * y) + phase)
                 for amp, fx, fy, phase in COLOR_WAVES]
        lum = 3000 + waves[0] + waves[1]
        chroma = waves[2] if scene == "color" else 0.0
        q = waves[3] if scene == "color" else 0.0
        return np.stack((lum + chroma, lum + q, lum - chroma), axis=-1)
    raise ValueError(f"unknown scene {scene!r}")


def _validated_rgb(value, mask):
    a = finite_array(value, "RGB")
    m = np.asarray(mask)
    if a.ndim not in (3, 4) or a.shape[-1] != 3:
        raise ValueError("expected RGB image or repeat stack")
    if m.dtype != np.bool_ or m.shape != a.shape[-3:-1] or not m.any():
        raise ValueError("nonempty Boolean spatial mask required")
    return a, m


def error(output, reference, mask):
    a, m = _validated_rgb(output, mask)
    b, _ = _validated_rgb(reference, mask)
    if a.ndim != 3 or a.shape != b.shape:
        raise ValueError("error expects matching RGB images")
    d = a[m] - b[m]
    mse = np.mean(d * d, axis=0)
    return {"pixels": int(m.sum()), "bias_dn": d.mean(axis=0).tolist(),
            "mse_dn2": mse.tolist(), "rmse_dn": np.sqrt(mse).tolist()}


def repeat_error(outputs, reference, mask):
    a, m = _validated_rgb(outputs, mask)
    ref, _ = _validated_rgb(reference, mask)
    if a.ndim != 4 or len(a) < 2 or a.shape[1:] != ref.shape:
        raise ValueError("temporal estimate needs two or more matching repeats")
    n = len(a)
    v = np.var(a, axis=0, ddof=1)[m].mean(axis=0)
    mean_mse = np.mean((a.mean(axis=0)[m] - ref[m]) ** 2, axis=0)
    mse_each = np.mean((a[:, m, :] - ref[m]) ** 2, axis=1)
    overall = mse_each.mean(axis=0)
    sem = mse_each.std(axis=0, ddof=1) / math.sqrt(n)
    decomposition = mean_mse + (n - 1) / n * v
    return {
        "repeats": n, "pixels": int(m.sum()),
        "mse_each_dn2": mse_each.tolist(),
        "mse_mean_dn2": overall.tolist(), "mse_sem_dn2": sem.tolist(),
        "rmse_from_mean_mse_dn": np.sqrt(overall).tolist(),
        "bias_of_repeat_mean_dn": (a.mean(axis=0)[m] - ref[m]).mean(axis=0).tolist(),
        "temporal_variance_dn2": v.tolist(), "temporal_sigma_dn": np.sqrt(v).tolist(),
        "repeat_mean_mse_dn2": mean_mse.tolist(),
        "finite_repeat_subtraction_dn2": (v / n).tolist(),
        "unclipped_squared_bias_estimate_dn2": (mean_mse - v / n).tolist(),
        "arithmetic_decomposition_residual_dn2": (overall - decomposition).tolist(),
        "decomposition_status": "DERIVED arithmetic identity, not independent evidence",
        "uncertainty_scope": "SEM across independent whole-image repeat MSEs; no pixel independence assumption",
    }


def paired_error(full, single, reference, mask):
    """Full minus single, using matched repeats, not independent-arm errors."""
    a, m = _validated_rgb(full, mask)
    b, _ = _validated_rgb(single, mask)
    if a.ndim != 4 or len(a) < 3 or a.shape != b.shape:
        raise ValueError("paired readout needs at least three matching repeats")
    aa, bb = repeat_error(a, reference, m), repeat_error(b, reference, m)
    delta = np.asarray(aa["mse_each_dn2"]) - np.asarray(bb["mse_each_dn2"])
    n = len(a)
    v_delta = np.var(a, axis=0, ddof=1)[m].mean(axis=0) - np.var(b, axis=0, ddof=1)[m].mean(axis=0)
    leave_one_out = []
    for omitted in range(n):
        keep = np.arange(n) != omitted
        av = np.var(a[keep], axis=0, ddof=1)[m].mean(axis=0)
        bv = np.var(b[keep], axis=0, ddof=1)[m].mean(axis=0)
        leave_one_out.append(av - bv)
    loo = np.asarray(leave_one_out)
    jackknife_se = np.sqrt((n - 1) / n * np.sum((loo - loo.mean(axis=0)) ** 2, axis=0))
    return {"direction": "full9 minus single4; negative error/variance difference favors full9 on that component",
            "repeat_mse_difference_dn2": delta.tolist(),
            "mean_mse_difference_dn2": delta.mean(axis=0).tolist(),
            "mse_difference_sem_dn2": (delta.std(axis=0, ddof=1) / math.sqrt(n)).tolist(),
            "temporal_variance_difference_dn2": v_delta.tolist(),
            "variance_difference_jackknife_se_dn2": jackknife_se.tolist(),
            "leave_one_out_variance_difference_dn2": loo.tolist(),
            "uncertainty_scope": "paired whole-image repeats; delete-one-repeat variance uncertainty is a small-sample diagnostic"}


def wave_response(rgb, x, y, mask, frequencies=None):
    a, m = _validated_rgb(rgb, mask)
    if a.ndim != 3 or np.shape(x) != m.shape or np.shape(y) != m.shape:
        raise ValueError("wave response expects one RGB image with its coordinates")
    frequencies = frequencies or [(v[1], v[2]) for v in PLANE_WAVES]
    columns = [np.ones(int(m.sum()))]
    for fx, fy in frequencies:
        phase = 2 * np.pi * (fx * np.asarray(x)[m] + fy * np.asarray(y)[m])
        columns.extend((np.cos(phase), np.sin(phase)))
    design = np.stack(columns, axis=1)
    coeff, _, rank, singular = np.linalg.lstsq(design, a[m], rcond=None)
    if rank != design.shape[1]:
        raise ValueError("wave readout is rank deficient on this mask")
    waves = []
    for i, (fx, fy) in enumerate(frequencies):
        c, s = coeff[1 + 2 * i:3 + 2 * i]
        waves.append({"frequency_native": [float(fx), float(fy)],
                      "amplitude_dn": np.hypot(c, s).tolist(),
                      "phase_rad": np.arctan2(-s, c).tolist()})
    return {"constant_dn": coeff[0].tolist(), "waves": waves,
            "design_condition": float(singular[0] / singular[-1]),
            "scope": "joint readout of registered waves, not output normalization"}


def read_tiff(path: Path, *, require_writer_description=True):
    import tifffile
    with tifffile.TiffFile(path) as f:
        if len(f.pages) != 1:
            raise ValueError("exactly one TIFF image required")
        page = f.pages[0]
        # Fixed CameraLinear contract. TIFF numeric arrays alone do not prove
        # how their spatial orientation or color would be interpreted.
        allowed_tags = {256, 257, 258, 259, 262, 270, 273, 274, 277, 278,
                        279, 282, 283, 284, 296, 305, 317, 339}
        unexpected = set(page.tags.keys()) - allowed_tags
        if unexpected:
            raise ValueError(f"unsupported CameraLinear TIFF metadata: {sorted(unexpected)}")
        orientation = int(page.tags[274].value) if 274 in page.tags else 1
        if orientation != 1:
            raise ValueError("TIFF orientation changes the declared canonical map")
        description = str(page.tags[270].value) if 270 in page.tags else None
        if require_writer_description and description != CAMERA_LINEAR_DESCRIPTION:
            raise ValueError("TIFF description does not declare the fixed camera-linear/WB disposition")
        if int(page.compression) != 1 or int(page.planarconfig) != 1:
            raise ValueError("expected uncompressed contiguous RGB baseline")
        pixels = page.asarray()
        if pixels.dtype != np.dtype("uint16") or pixels.ndim != 3 or pixels.shape[-1] != 3:
            raise ValueError("expected RGB16 TIFF")
        if int(page.photometric) != 2:
            raise ValueError("expected RGB photometric interpretation")
        info = {"path": str(path.resolve()), "bytes": path.stat().st_size,
                "file_sha256": sha256(path),
                "pixel_sha256": array_hash(pixels.astype("<u2", copy=False)),
                "width": int(pixels.shape[1]), "height": int(pixels.shape[0]),
                "channels": 3, "dtype": "uint16",
                "orientation": orientation, "icc": "absent", "transfer_tags": "absent",
                "image_description": description,
                "tag_codes": sorted(page.tags.keys()),
                "rail_zero_by_channel": (pixels == 0).sum(axis=(0, 1)).tolist(),
                "rail_max_by_channel": (pixels == 65535).sum(axis=(0, 1)).tolist(),
                "software": str(page.tags.get("Software").value) if "Software" in page.tags else None}
    return pixels.astype(np.float64) * ((WHITE - BLACK) / 65535.0), info


def commission():
    """Finite predeclared component controls. Independent review is separate."""
    x, y = canonical_grid(144, 112, 7, 11)
    mask = np.ones(x.shape, dtype=bool)
    truth = target("color", x, y)
    checks = {}
    evidence = {}
    clean = error(truth, truth, mask)
    checks["exact_target_noop"] = max(clean["mse_dn2"]) == 0.0
    shifted = truth.copy()
    shifted[..., 0] += 20
    offset = error(shifted, truth, mask)
    checks["known_offset"] = abs(offset["bias_dn"][0] - 20) < 1e-8 and abs(offset["mse_dn2"][0] - 400) < 1e-8
    checks["color_swap"] = min(error(truth[..., ::-1], truth, mask)["mse_dn2"][::2]) > 1
    evidence["offset"] = offset

    # Use a periodic wave with exact integer cycles for a blur with no boundary ambiguity.
    fx, fy, phase = 1 / 12, 1 / 16, 0.31
    theta = 2 * np.pi * (fx * x + fy * y)
    periodic = np.repeat((3000 + 300 * np.cos(theta + phase))[..., None], 3, axis=2)
    attenuation = math.exp(-2 * math.pi**2 * 0.6**2 * (fx * fx + fy * fy))
    blurred = 3000 + (periodic - 3000) * attenuation
    response = wave_response(blurred, x, y, mask, [(fx, fy)])
    checks["known_blur"] = abs(response["waves"][0]["amplitude_dn"][0] - 300 * attenuation) < 1e-8 and min(error(blurred, periodic, mask)["mse_dn2"]) > 1
    phaseshift = np.repeat((3000 + 300 * np.cos(theta + phase + 0.4))[..., None], 3, axis=2)
    phase_readout = wave_response(phaseshift, x, y, mask, [(fx, fy)])
    checks["known_phase"] = abs(phase_readout["waves"][0]["phase_rad"][0] - (phase + 0.4)) < 1e-8
    evidence["periodic_blur"] = {"known_sigma_native": 0.6, "amplitude_factor": attenuation,
                                  "response": response, "error": error(blurred, periodic, mask)}
    flat = np.full_like(truth, 3000)
    checks["flat_blur_noop"] = max(error(3000 + (flat - 3000) * attenuation, flat, mask)["mse_dn2"]) == 0

    noisy = flat + np.random.default_rng(81271).normal(0, 8, size=(64, *flat.shape))
    noise = repeat_error(noisy, flat, mask)
    variance = np.array(noise["temporal_variance_dn2"])
    checks["independent_noise"] = bool(np.all(np.abs(variance / 64 - 1) <= 0.03))
    averaged = np.zeros_like(noisy)
    rng = np.random.default_rng(92147)
    for _ in range(16):
        averaged += rng.normal(0, 8, size=averaged.shape) / 16
    averaged += flat
    mean_noise = repeat_error(averaged, flat, mask)
    mean_variance = np.array(mean_noise["temporal_variance_dn2"])
    checks["sixteen_copy_mean"] = bool(np.all(np.abs(mean_variance / 4 - 1) <= 0.03))
    identical = repeat_error(np.repeat(noisy[:1], 8, axis=0), flat, mask)
    checks["identical_noise_not_independent"] = max(identical["temporal_variance_dn2"]) < 1e-20 and min(identical["mse_mean_dn2"]) > 1
    deterministic = repeat_error(np.repeat(truth[None], 8, axis=0), truth, mask)
    checks["structure_not_temporal_noise"] = max(deterministic["temporal_variance_dn2"]) < 1e-20
    checks["mse_identity_arithmetic_only"] = max(abs(v) for v in noise["arithmetic_decomposition_residual_dn2"]) < 1e-8
    evidence["noise"] = noise
    evidence["sixteen_copy_mean"] = mean_noise
    evidence["variance_ratio_noise_to_mean"] = (variance / mean_variance).tolist()
    evidence["identical_noise"] = identical
    for name, bad_mask, bad_rgb in [("empty", np.zeros_like(mask), truth),
                                    ("wrong_shape", mask[:-1], truth),
                                    ("nonfinite", mask, truth * np.nan)]:
        try:
            error(bad_rgb, truth, bad_mask)
        except ValueError:
            checks[f"refuse_{name}"] = True
        else:
            checks[f"refuse_{name}"] = False
    return {"schema": "m194b-scorer-commission-v1", "source_sha256": sha256(Path(__file__)),
            "scope": "author component controls; independent verifier must re-choose inputs",
            "checks": checks, "pass": all(checks.values()), "evidence": evidence}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--commission", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if not args.commission:
        p.error("consumer receipt integration is not yet implemented")
    if args.out.exists():
        raise FileExistsError("retain prior result; use a fresh output path")
    result = commission()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "checks": result["checks"]}))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
