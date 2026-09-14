"""Original sensor samples in the common reference149 native coordinate system."""
from pathlib import Path
import hashlib
import json
import numpy as np

HERE = Path(__file__).resolve().parent


def load():
    source = HERE / "joint-raw-samples-2"
    receipt = json.loads((source / "receipt.json").read_text())
    wb = np.asarray(receipt["wb_bits"], dtype=np.uint32).view(np.float32)
    black, white = np.asarray(receipt["levels"], dtype=np.float32)
    inv_range = np.float32(1) / (white-black)
    gain = np.float32(receipt["noise"]["gain_dn_per_e"])
    read_dn = np.float32(receipt["noise"]["read_noise_dn"])
    height, width = receipt["native_sensor_shape"]
    center = complex(width/2, height/2)
    origin = complex(*receipt["target_origin_native"])
    parts = {key: [] for key in ("xy", "values", "variance", "channels", "valid", "frame")}
    for frame in receipt["frames"]:
        index = frame["index"]
        raw = np.load(source/f"frame-{index}-cfa.npy", allow_pickle=False)
        assert raw.dtype == np.uint16
        assert hashlib.sha256(raw.tobytes()).hexdigest() == frame["raw_u16_sha256"]
        x0, y0, w, h = frame["source_xywh"]
        assert raw.shape == (h, w)
        yy, xx = np.indices((h, w), dtype=np.int32)
        xx += x0
        yy += y0
        a, b = complex(*frame["a"]), complex(*frame["b_plane"])
        ref = center + (xx + 1j*yy - center - 2*b)/a - origin
        channels = np.where((xx+yy) % 2 == 1, 1, np.where(yy % 2 == 0, 0, 2)).astype(np.uint8)
        signal = np.maximum(raw.astype(np.float32)-black, np.float32(0))
        values = signal * wb[channels] * inv_range  # Preserve product arithmetic order.
        scale = wb[channels] * inv_range
        variance = (gain*signal + read_dn*read_dn) * scale*scale
        parts["xy"].append(np.column_stack((ref.real.ravel(), ref.imag.ravel())))
        parts["values"].append(values.ravel())
        parts["variance"].append(variance.ravel())
        parts["channels"].append(channels.ravel())
        parts["valid"].append((raw < 16383).ravel())
        parts["frame"].append(np.full(raw.size, index, dtype=np.int16))
    result = {key: np.concatenate(value, axis=0) for key, value in parts.items()}
    assert result["xy"].dtype == np.float64
    assert result["values"].dtype == result["variance"].dtype == np.float32
    assert np.isfinite(result["values"]).all() and (result["variance"] > 0).all()
    return tuple(receipt["target_shape"]), result, receipt
