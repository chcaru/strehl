"""M126 composite: overview render for deliberate crop selection.

Reads the LINEAR camera-native 16-bit output. Hard tifffile import + dtype
assert: PIL.Image.open silently downconverts 16-bit TIFFs (241 corrupted
measurements in this project's history).

Display transform is fixed from ARM A only and applied identically to every
arm, so any visible difference between arms is real and not a tone-mapping
artefact. It is for LOOKING, not for measuring.
"""
import sys, json
import numpy as np
import tifffile  # hard import on purpose -- no PIL fallback
from PIL import Image  # WRITE ONLY, 8-bit -- never used to read a 16-bit TIFF


def save_png(path, arr8):
    assert arr8.dtype == np.uint8, arr8.dtype
    Image.fromarray(arr8).save(path)

TAG = sys.argv[1] if len(sys.argv) > 1 else "109MSDCF"
ROOT = rf"C:\dev\strehl-out\M126-COMPOSITE\{TAG}"


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: dtype {a.dtype}, expected uint16"
    return a


def fit_display(ref):
    """Per-channel gain + gamma fitted on the reference arm only."""
    f = ref.astype(np.float32)
    lo = np.array([np.percentile(f[..., c], 0.5) for c in range(3)], np.float32)
    hi = np.array([np.percentile(f[..., c], 99.7) for c in range(3)], np.float32)
    return lo, hi


def apply_display(a, lo, hi, gamma=1 / 2.2):
    f = (a.astype(np.float32) - lo) / np.maximum(hi - lo, 1.0)
    f = np.clip(f, 0.0, 1.0) ** gamma
    return (f * 255.0 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    ref = load(rf"{ROOT}\lin\A.tif")
    print(f"A.tif shape={ref.shape} dtype={ref.dtype}")
    lo, hi = fit_display(ref)
    print(f"display lo={lo.tolist()} hi={hi.tolist()}")
    json.dump({"lo": lo.tolist(), "hi": hi.tolist(), "shape": list(ref.shape)},
              open(rf"{ROOT}\display.json", "w"))
    disp = apply_display(ref, lo, hi)
    # integer decimation only -- no resampling, no interpolation
    step = max(1, max(ref.shape[0], ref.shape[1]) // 1400)
    save_png(rf"{ROOT}\overview_A.png", disp[::step, ::step])
    print(f"overview step={step} -> {disp[::step, ::step].shape}")
