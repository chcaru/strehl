"""Original explicit cache-to-predictor color contract, with FP32 pixel arithmetic.

Stored RGB remains encoded sRGB. Decode before converting standard BT.709/D65
primaries to linear ProPhoto/D50 using declared Bradford white adaptation. Masks
are probabilities/weights, never color channels. This does not reproduce a RAW
developer, choose a tone curve, or claim Adobe's exact adaptation coefficients.

Numeric primaries: https://www.color.org/chardata/rgb/srgb.xalter and
https://www.color.org/chardata/rgb/ROMMRGB.pdf . The transfer is IEC sRGB.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


LEGACY_DOMAIN = "display-rgb-research-v1"
LINEAR_DOMAIN = "linear-prophoto-d50-bradford-from-srgb-v1"
# Column-vector convention: destination = M @ source. Derived from published xy
# primaries/whites and Bradford adaptation; independently recomputed below.
LINEAR_709_TO_PROPHOTO = np.array([
    [.5292804, .330153, .1405666],
    [.09836622, .8734639, .028169824],
    [.016875342, .11765941, .8654652],
], dtype=np.float32)


def contract_descriptor(domain: str = LINEAR_DOMAIN, storage_dtype: str = "uint8") -> dict:
    if domain not in (LEGACY_DOMAIN, LINEAR_DOMAIN) or storage_dtype not in ("uint8", "float32"):
        raise ValueError("unsupported explicit predictor/storage contract")
    result = {"schema": 1, "domain": domain, "layout": "NCHW", "shape": [5, 384, 512],
              "storage_dtype": storage_dtype, "arithmetic_dtype": "float32",
              "storage_scale": 255 if storage_dtype == "uint8" else 1,
              "channel_order": ["red", "green", "blue", "subject_weight", "sky_weight"],
              "storage_rgb": "encoded-srgb" if domain == LINEAR_DOMAIN else "legacy-camera-display-research-rgb",
              "model_rgb": "linear-prophoto-d50" if domain == LINEAR_DOMAIN else "unchanged-normalized-legacy-rgb",
              "mask_transform": "divide-by-storage-scale-only",
              "current_dataset_range": "normalized SDR source [0,1]; does not establish native HDR input bounds"}
    if domain == LINEAR_DOMAIN:
        result.update({"decode": {"breakpoint": .04045, "linear_divisor": 12.92,
                                  "offset": .055, "scale": 1.055, "power": 2.4},
                       "white_adaptation": "Bradford D65 xy(.3127,.3290) to D50 xy(.3457,.3585)",
                       "matrix_column_vector": LINEAR_709_TO_PROPHOTO.tolist(),
                       "rgb_clipping": "none", "conversion_order": "FP32 scale, sRGB decode, primary matrix"})
    return result


def contract_sha256(descriptor: dict) -> str:
    canonical = json.dumps(descriptor, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def implementation_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def validate_descriptor(descriptor: dict) -> None:
    expected = contract_descriptor(descriptor.get("domain"), descriptor.get("storage_dtype"))
    if descriptor != expected:
        raise ValueError("predictor contract differs from this supported mathematical definition")


def select_manifest_contract(manifest: dict, manifest_sha256: str | None = None) -> dict:
    if "model_input_contract" in manifest:
        descriptor = manifest["model_input_contract"]
        validate_descriptor(descriptor)
        if manifest.get("model_input_contract_sha256") != contract_sha256(descriptor):
            raise ValueError("manifest predictor-contract digest mismatch")
        return descriptor
    # Public caches always declare their contract. A cache digest cannot stand
    # in for a portable description of color encoding and mask semantics.
    raise ValueError("cache requires an explicit model_input_contract and matching digest")


def prepare_numpy(stored: np.ndarray, descriptor: dict) -> np.ndarray:
    validate_descriptor(descriptor)
    if stored.ndim != 4 or tuple(stored.shape[1:]) != (5, 384, 512):
        raise ValueError("stored predictor input must be [N,5,384,512]")
    if stored.dtype != np.dtype(descriptor["storage_dtype"]):
        raise ValueError("stored input dtype differs from manifest contract")
    values = np.array(stored, dtype=np.float32, copy=True) / np.float32(descriptor["storage_scale"])
    if not np.isfinite(values).all() or not ((values >= 0) & (values <= 1)).all():
        raise ValueError("encoded SDR source/masks must be finite in [0,1]")
    if descriptor["domain"] == LINEAR_DOMAIN:
        rgb = values[:, :3]
        linear = np.where(rgb <= np.float32(.04045), rgb / np.float32(12.92),
                          ((rgb + np.float32(.055)) / np.float32(1.055)) ** np.float32(2.4))
        values[:, :3] = np.einsum("ij,bjhw->bihw", LINEAR_709_TO_PROPHOTO, linear, optimize=True)
    return values


def prepare_torch(stored, descriptor: dict):
    """Lazy CPU/CUDA conversion outside the neural model; gradients are preserved."""
    import torch
    validate_descriptor(descriptor)
    dtype = torch.uint8 if descriptor["storage_dtype"] == "uint8" else torch.float32
    if stored.ndim != 4 or tuple(stored.shape[1:]) != (5, 384, 512) or stored.dtype != dtype:
        raise ValueError("torch input shape/dtype differs from manifest contract")
    values = stored.to(dtype=torch.float32) / float(descriptor["storage_scale"])
    # Cache preflight validates source ranges once; this hot path avoids GPU
    # scalar synchronization. The caller may validate untrusted inputs separately.
    if descriptor["domain"] == LINEAR_DOMAIN:
        rgb = values[:, :3]
        linear = torch.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055).pow(2.4))
        matrix = torch.as_tensor(LINEAR_709_TO_PROPHOTO, dtype=torch.float32, device=stored.device)
        converted = torch.matmul(linear.permute(0, 2, 3, 1), matrix.T).permute(0, 3, 1, 2)
        values = torch.cat((converted, values[:, 3:]), dim=1)
    return values


def commission() -> dict:
    """Independent analytic/colorimetric and NumPy/Torch controls, CPU only."""
    import torch
    torch.set_num_threads(1)
    # Re-derive the matrix from chromaticities rather than reuse its coefficients.
    def white(xy):
        x, y = map(np.float32, xy)
        return np.array([x / y, 1, (np.float32(1) - x - y) / y], dtype=np.float32)

    def rgb_xyz(primaries, xy):
        columns = np.stack([white(p) for p in primaries], axis=1)
        return columns @ np.diag(np.linalg.solve(columns, white(xy)))

    d65, d50 = (.3127, .3290), (.3457, .3585)
    source = rgb_xyz(((.64, .33), (.30, .60), (.15, .06)), d65)
    destination = rgb_xyz(((.7347, .2653), (.1596, .8404), (.0366, .0001)), d50)
    bradford = np.array([[.8951, .2664, -.1614], [-.7502, 1.7135, .0367], [.0389, -.0685, 1.0296]], np.float32)
    adaptation = np.linalg.solve(bradford, np.diag((bradford @ white(d50)) / (bradford @ white(d65))) @ bradford)
    derived = np.linalg.solve(destination, adaptation @ source)
    np.testing.assert_allclose(LINEAR_709_TO_PROPHOTO, derived, rtol=2e-6, atol=2e-7)
    descriptor = contract_descriptor(storage_dtype="float32")
    fixture = np.zeros((1, 5, 384, 512), dtype=np.float32)
    fixture[:, :3] = .5
    fixture[:, 3], fixture[:, 4] = .17, .83
    out = prepare_numpy(fixture, descriptor)
    # A neutral encoded half-code has known IEC sRGB linear luminance and remains
    # neutral under a white-adapted RGB-primary change.
    np.testing.assert_allclose(out[0, :3, 0, 0], [.21404114] * 3, atol=2e-7)
    np.testing.assert_array_equal(out[:, 3:], fixture[:, 3:])
    fixture[:, :3] = np.array([1, 0, 0], np.float32)[None, :, None, None]
    red = prepare_numpy(fixture, descriptor)
    np.testing.assert_allclose(red[0, :3, 0, 0], derived[:, 0], atol=2e-7)
    if np.allclose(red[0, :3, 0, 0], derived[0]):
        raise AssertionError("matrix test cannot distinguish row/column transposition")
    rng = np.random.default_rng(41022)
    stored = rng.integers(0, 256, (1, 5, 384, 512), dtype=np.uint8)
    descriptor = contract_descriptor()
    numpy_output = prepare_numpy(stored, descriptor)
    torch_output = prepare_torch(torch.from_numpy(stored), descriptor).numpy()
    np.testing.assert_allclose(torch_output, numpy_output, rtol=3e-6, atol=3e-7, equal_nan=False)
    legacy = contract_descriptor(LEGACY_DOMAIN)
    np.testing.assert_array_equal(prepare_numpy(stored, legacy), stored.astype(np.float32) / np.float32(255))
    # This dark code is below one linear8-bit quantization step. It must survive
    # conversion; converting to linear uint8 would erase it.
    stored.fill(1)
    dark = prepare_numpy(stored, descriptor)
    assert 0 < dark[0, 0, 0, 0] < 1 / 255
    return {"passed": True, "domain": LINEAR_DOMAIN, "model_input_contract_sha256": contract_sha256(descriptor),
            "numpy_torch_max_absolute": float(np.max(np.abs(torch_output - numpy_output))),
            "legacy_unchanged": True, "linear_uint8_storage_used": False,
            "scope": "original standard color math, not Adobe RAW/tone/display parity"}


if __name__ == "__main__":
    print(json.dumps(commission(), indent=2))
