"""Saved-CFA regression: reject replicated-edge residuals, preserve padded sites."""
from pathlib import Path
import importlib.util
import json
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ri_boundary", HERE / "residual-interpolation.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
source_path = HERE / "matched-chip-on-1/pale-circuit-frame149-raw-cfa.f32"
cfa = np.fromfile(source_path, dtype="<f4").reshape(392, 392)
y, x = np.indices(cfa.shape)
masks = ((y % 2 == 0) & (x % 2 == 0), (y + x) % 2 == 1,
         (y % 2 == 1) & (x % 2 == 1))
scaled = cfa * np.float32(255)
sparse = np.zeros((*cfa.shape, 3), dtype=np.float32)
for c, mask in enumerate(masks):
    sparse[..., c][mask] = scaled[mask]
unpad = adapter.demosaic_RI(sparse, "rggb", np.float32(1), "RI")
bound = np.float32(16)*np.float32(np.finfo(np.float32).eps)*max(
    np.float32(1), np.max(np.abs(unpad)), np.max(np.abs(scaled)))
edge = (x == 0) | (y == 0) | (x == cfa.shape[1]-1) | (y == cfa.shape[0]-1)
failures = []
for c, mask in enumerate(masks):
    bad = mask & (np.abs(unpad[..., c] - scaled) > bound)
    assert not np.any(bad & ~edge), "unpadded defect escaped the outermost edge"
    failures.append(int(np.count_nonzero(bad)))
assert failures[0] > 0 and failures[2] > 0 and failures[1] == 0, "negative control did not exercise replicated R/B residuals"
padded = adapter.ri(cfa)
assert padded.dtype == np.float32 and padded.shape == sparse.shape and np.isfinite(padded).all()
for c, mask in enumerate(masks):
    assert np.array_equal(padded[..., c][mask].view(np.uint32), cfa[mask].view(np.uint32)), "measured sample changed"
assert adapter.LAST_DIAGNOSTIC["known_samples_bit_exact"]
print(json.dumps({"status": "RI_BOUNDARY_CONTROL_PASS", "source": str(source_path),
    "unpadded_beyond_roundoff_rgb": failures, "unpadded_guard_reference_units": float(bound),
    "padded": adapter.LAST_DIAGNOSTIC}))
