"""One saved chip CFA: locate the refused known-sample residual, no render."""
from pathlib import Path
import importlib.util
import json
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ri_diagnosis", HERE / "residual-interpolation.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
path = HERE / "matched-chip-on-1/pale-circuit-frame149-raw-cfa.f32"
a = np.fromfile(path, dtype="<f4").reshape(392, 392)
y, x = np.indices(a.shape)
masks = ((y % 2 == 0) & (x % 2 == 0), (y + x) % 2 == 1, (y % 2 == 1) & (x % 2 == 1))
scaled = a * np.float32(255)
source = np.zeros((*a.shape, 3), dtype=np.float32)
for c, mask in enumerate(masks):
    source[..., c][mask] = scaled[mask]
rgb = adapter.demosaic_RI(source, "rggb", np.float32(1), "RI")
bound = np.float32(16)*np.float32(np.finfo(np.float32).eps)*max(np.float32(1), np.max(np.abs(rgb)), np.max(np.abs(scaled)))
results = []
for c, mask in enumerate(masks):
    error = np.abs(rgb[..., c] - scaled)
    for trim in (0, 1, 2, 12, 32):
        valid = mask & (x >= trim) & (y >= trim) & (x < a.shape[1]-trim) & (y < a.shape[0]-trim)
        scores = np.where(valid, error, np.float32(-1))
        at = np.unravel_index(np.argmax(scores), scores.shape)
        results.append(dict(channel="RGB"[c], trim=trim, max_error_reference_units=float(error[at]),
            at_yx=list(map(int, at)), expected=float(scaled[at]), got=float(rgb[at[0],at[1],c]),
            beyond_roundoff=int(np.count_nonzero(valid & (error > bound)))))
result = dict(source=str(path), dtype=str(rgb.dtype), original_guard=float(bound), results=results)
out = HERE / "ri-guard-diagnosis-1.json"
with out.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps(result))
