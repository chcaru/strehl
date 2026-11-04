"""Bound complete reconstruction files and test native fallback in delivered pixels."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import tifffile

p = argparse.ArgumentParser()
p.add_argument("native", type=Path)
p.add_argument("candidate", type=Path)
p.add_argument("out", type=Path)
a = p.parse_args()
def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
def read(path):
    return json.loads(path.read_text())
assert read(a.candidate / "completed.json")
report = read(a.candidate / "render-report.json")
native_report = read(a.native / "render-report.json")
sr = report["reconstruction"]
geometry = read(a.candidate / "reconstruction/geometry.json")
assert sha(a.candidate / "reconstruction/geometry.json") == sr["geometry_sha256"]
assert sha(a.candidate / "reconstruction/tiles.json") == sr["tiles_receipt"]["sha256"]
assert report["canvas"] == native_report["canvas"]
assert read(a.candidate / "alignment.json")["warpmap"] == read(a.native / "alignment.json")["warpmap"]
assert sha(a.candidate / "source-identities.json") == sha(a.native / "source-identities.json")
for binding in geometry["files"]:
    path = a.candidate / "reconstruction" / binding["path"]
    assert path.stat().st_size == binding["bytes"] and sha(path) == binding["sha256"]
support = tifffile.memmap(a.candidate / "reconstruction/support.tiff", mode="r")
reasons = tifffile.memmap(a.candidate / "reconstruction/fallback-reason.tiff", mode="r")
width, height = geometry["dimensions"]
assert support.shape == reasons.shape == (height, width)
assert [2*report["canvas"][0], 2*report["canvas"][1]] == geometry["origin_sensor"]
assert geometry["step_sensor"] == [1, 1]
counts = np.zeros(13, dtype=np.int64)
changed = {"master.tiff": 0, "photograph.tiff": 0}
files = {}
for name in changed:
    old, new = [tifffile.memmap(root / name, mode="r") for root in (a.native, a.candidate)]
    assert old.shape == new.shape == (height, width, 3) and old.dtype == new.dtype
    for y in range(0, height, 128):
        s, r = support[y:y+128], reasons[y:y+128]
        assert np.isfinite(s).all() and np.isfinite(r).all()
        assert np.isin(s, [0, 1]).all() and ((r >= 0) & (r < 13) & (r == np.floor(r))).all()
        assert np.array_equal(s == 1, r == 0)
        x, z = old[y:y+128], new[y:y+128]
        assert np.isfinite(x).all() and np.isfinite(z).all()
        different = np.any(x.view(np.uint8).reshape(x.shape[:2] + (-1,)) != z.view(np.uint8).reshape(z.shape[:2] + (-1,)), axis=2)
        assert not np.any(different & (s == 0)), (name, y, "native fallback changed")
        changed[name] += int(different.sum())
        if name == "master.tiff":
            counts += np.bincount(r.astype(np.int64).ravel(), minlength=13)
    files[name] = {"sha256": sha(a.candidate/name), "native_sha256": sha(a.native/name),
                   "shape": list(new.shape), "dtype": str(new.dtype), "changed_pixels": changed[name],
                   "all_pixels_finite": True, "native_fallback_pixel_bits_identical": True}
    del old, new
assert int(counts.sum()) == sr["total_rgb_pixels"] == height * width
assert int(counts[0]) == sr["replaced_rgb_pixels"]
for code, label in geometry["fallback_reasons"].items():
    assert int(counts[int(code)]) == sr["reason_counts"][label]
audit = {"schema": "strehl.complete-reconstruction-readback.v1", "candidate": str(a.candidate),
    "native": str(a.native), "sources_and_saved_warp_identical": True, "maps_and_tiles_bound": True,
    "reason_counts": counts.tolist(), "reported_supported_pixels": sr["replaced_rgb_pixels"], "files": files,
    "scope": "Complete-file mechanics and exact fallback; no photographic or resolution-gain claim."}
with a.out.open("x", encoding="utf-8") as out:
    json.dump(audit, out, indent=2)
    out.write("\n")
print(json.dumps(audit, indent=2))
