"""Compare unchanged original selection and exact consuming geometry across builds."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("before", type=Path)
p.add_argument("after", type=Path)
p.add_argument("out", type=Path)
p.add_argument("--count", type=int, required=True)
a = p.parse_args()
def records(path):
    rows = []
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        first = stream.readline()
        assert first == b'{"schema":"strehl.original-cfa-tiles.v1","tiles":[\n'
        digest.update(first)
        while len(rows) < a.count:
            line = stream.readline()
            assert line.endswith(b"\n"), "requested prefix is not complete"
            rows.append(json.loads(line.rstrip(b",\r\n")))
            digest.update(line)
    return rows, digest.hexdigest()
before, before_sha = records(a.before)
after, after_sha = records(a.after)
excluded = {"seconds", "replaced_rgb_pixels", "region_sampler_peak_bytes"}
different, witnessed = [], 0
for index, (old, new) in enumerate(zip(before, after)):
    witnessed += int("certificates" in old)
    x, y = [{k: v for k, v in row.items() if k not in excluded} for row in (old, new)]
    if x != y:
        different.append({"tile": index, "fields": sorted(k for k in x.keys() | y.keys() if x.get(k) != y.get(k))})
report = {"schema": "strehl.reconstruction-registration-comparison.v1", "before": str(a.before), "after": str(a.after),
          "complete_prefix_tiles": a.count, "before_prefix_sha256": before_sha, "after_prefix_sha256": after_sha,
          "excluded_fields": sorted(excluded), "witnessed_tiles": witnessed,
          "differences": different, "source_selection_and_exact_geometry_equal": not different,
          "scope": "Source planning, native retention, training/heldout graph and exact consuming-pull bits; appearance admission intentionally differs."}
with a.out.open("x", encoding="utf-8") as out:
    json.dump(report, out, indent=2)
    out.write("\n")
print(json.dumps(report, indent=2))
assert not different
