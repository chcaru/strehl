"""Freeze complete tile records from an in-progress baseline, never its partial tail."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("tiles", type=Path)
p.add_argument("out", type=Path)
p.add_argument("--count", type=int, default=1024)
a = p.parse_args()
records, prefix = [], bytearray()
with a.tiles.open("rb") as stream:
    first = stream.readline()
    assert first == b'{"schema":"strehl.original-cfa-tiles.v1","tiles":[\n'
    prefix.extend(first)
    while len(records) < a.count:
        line = stream.readline()
        if not line.endswith(b",\n"):
            break
        row = json.loads(line[:-2])
        records.append({k: row[k] for k in ("rect", "sources", "guides")})
        prefix.extend(line)
assert len(records) == a.count, (len(records), a.count)
with a.out.open("x", encoding="utf-8") as out:
    json.dump({"schema": "strehl.reconstruction-cohort-trace.v1", "baseline_tiles": str(a.tiles),
               "prefix_bytes": len(prefix), "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
               "selection": "first complete1024 baseline tile records; no image or timing selection",
               "tiles": records}, out, indent=2)
    out.write("\n")
print(json.dumps({"tiles": len(records), "prefix_bytes": len(prefix),
                  "trace_sha256": hashlib.sha256(a.out.read_bytes()).hexdigest()}))
