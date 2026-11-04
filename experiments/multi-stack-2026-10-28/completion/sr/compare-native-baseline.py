"""Compare two complete native session renders; no image transform or fitting."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("before", type=Path)
p.add_argument("after", type=Path)
p.add_argument("out", type=Path)
a = p.parse_args()
def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
def read(root, name):
    return json.loads((root / name).read_text())
for root in (a.before, a.after):
    assert read(root, "completed.json")
files = {}
for name in ("photograph.tiff", "master.tiff", "source-identities.json", "calibration.json", "photometry.json"):
    old, new = digest(a.before / name), digest(a.after / name)
    files[name] = {"before_sha256": old, "after_sha256": new, "equal": old == new}
before, after = [read(root, "render-report.json") for root in (a.before, a.after)]
fields = {key: {"before": before[key], "after": after[key], "equal": before[key] == after[key]}
          for key in ("canvas", "development_reference_pass", "primary_pass", "reference_pass")}
recipe = {key: {"before": before["recipe"][key], "after": after["recipe"][key],
                "equal": before["recipe"][key] == after["recipe"][key]}
          for key in ("bands", "gate", "exponent", "sharpen_per_octave", "resampler", "precision_weights", "precision_focus_reference", "workers", "memory_limit_gib")}
alignments = [read(root, "alignment.json") for root in (a.before, a.after)]
warpmap_equal = alignments[0]["warpmap"] == alignments[1]["warpmap"]
report = {"schema": "strehl.complete-native-baseline-comparison.v1", "before": str(a.before), "after": str(a.after),
          "files": files, "fields": fields, "recipe": recipe, "serialized_warpmap_equal": warpmap_equal,
          "photographic_files_byte_identical": all(files[n]["equal"] for n in ("photograph.tiff", "master.tiff"))}
with a.out.open("x", encoding="utf-8") as out:
    json.dump(report, out, indent=2)
    out.write("\n")
print(json.dumps(report, indent=2))
