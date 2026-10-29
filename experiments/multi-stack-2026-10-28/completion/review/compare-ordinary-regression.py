"""Complete photograph, linear RGB and native sensor-master bit comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import tifffile

p = argparse.ArgumentParser()
p.add_argument("baseline", type=Path)
p.add_argument("candidate", type=Path)
p.add_argument("out", type=Path)
a = p.parse_args()
def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
report = {"baseline": str(a.baseline.resolve()), "candidate": str(a.candidate.resolve()), "files": {}}
for name in ("photograph.tiff", "master.tiff", "sensor.tiff"):
    old, new = [tifffile.memmap(root / name, mode="r") for root in (a.baseline, a.candidate)]
    assert old.shape == new.shape and old.dtype == new.dtype, name
    hashes = [hashlib.sha256(), hashlib.sha256()]
    equal = finite = True
    for start in range(0, old.shape[0], 128):
        x, y = old[start:start+128], new[start:start+128]
        equal &= np.array_equal(x.view(np.uint8), y.view(np.uint8))
        finite &= bool(np.isfinite(x).all() and np.isfinite(y).all())
        hashes[0].update(np.ascontiguousarray(x).tobytes())
        hashes[1].update(np.ascontiguousarray(y).tobytes())
    report["files"][name] = {"shape": list(old.shape), "dtype": str(old.dtype),
        "pixel_bits_identical": bool(equal), "finite": finite,
        "baseline_pixel_sha256": hashes[0].hexdigest(), "candidate_pixel_sha256": hashes[1].hexdigest(),
        "whole_file_identical": sha(a.baseline/name) == sha(a.candidate/name)}
    del old, new
with a.out.open("x", encoding="utf-8") as out:
    json.dump(report, out, indent=2)
    out.write("\n")
print(json.dumps(report, indent=2))
assert all(row["pixel_bits_identical"] and row["finite"] for row in report["files"].values())
