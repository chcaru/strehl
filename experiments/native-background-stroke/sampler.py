"""Small same-CFA-phase ROI sampler; values f32, held geometry f64."""
from pathlib import Path
import importlib.util
import numpy as np

CLIB_PATH = Path(__file__).resolve().parents[1] / "M-PHASE0-PHASE/src/clib.py"
_spec = importlib.util.spec_from_file_location("background_existing_map", CLIB_PATH)
clib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(clib)


def sample(patch, origin, reference_rect, phase, transform, gauge="scene", direction="forward"):
    patch = np.asarray(patch)
    if patch.ndim != 2 or patch.dtype not in (np.dtype("uint16"), np.dtype("float32")):
        raise ValueError("expected a u16 or f32 mosaic patch")
    ox, oy = origin
    x, y, w, h = reference_rect
    dx, dy = phase
    if any(int(v) != v or v % 2 for v in (ox, oy, x, y, w, h)) or w <= 0 or h <= 0:
        raise ValueError("even native origins and positive even rectangle extents required")
    if phase not in ((0, 0), (1, 0), (0, 1), (1, 1)):
        raise ValueError("invalid original CFA phase")
    if gauge not in ("sensor", "scene") or direction not in ("forward", "inverse"):
        raise ValueError("unknown gauge/direction")
    a, b = transform
    if not all(np.isfinite(v) for v in (a.real, a.imag, b.real, b.imag)) or abs(a) == 0:
        raise ValueError("invalid similarity")
    if direction == "inverse":
        a, b = 1 / a, -b / a
    xx, yy = np.meshgrid(x + dx + 2 * np.arange(w // 2), y + dy + 2 * np.arange(h // 2))
    if gauge == "scene":
        # Reuse the project's documented reference -> source map and centre.
        points = [clib.apply_at(a, b, float(px) / 2, float(py) / 2, 1758, 1172)
                  for px, py in zip(xx.ravel(), yy.ravel())]
        mapped = np.asarray(points, dtype=np.float64).reshape(*xx.shape, 2)
        sx, sy = 2 * mapped[..., 0], 2 * mapped[..., 1]
    else:
        sx, sy = xx, yy
    px = (sx - ox - dx) / 2
    py = (sy - oy - dy) / 2
    plane = np.asarray(patch[dy::2, dx::2], dtype=np.float32)
    if (px.min() < 0 or py.min() < 0 or px.max() > plane.shape[1] - 1
            or py.max() > plane.shape[0] - 1):
        raise ValueError("requested source support leaves the fixed patch")
    ix, iy = np.floor(px).astype(np.intp), np.floor(py).astype(np.intp)
    jx, jy = np.minimum(ix + 1, plane.shape[1] - 1), np.minimum(iy + 1, plane.shape[0] - 1)
    fx, fy = (px - ix).astype(np.float32), (py - iy).astype(np.float32)
    top = plane[iy, ix] * (np.float32(1) - fx) + plane[iy, jx] * fx
    bottom = plane[jy, ix] * (np.float32(1) - fx) + plane[jy, jx] * fx
    result = top * (np.float32(1) - fy) + bottom * fy
    if not np.isfinite(result).all():
        raise ValueError("nonfinite sampled value")
    return result.astype(np.float32, copy=False)
