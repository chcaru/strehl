"""Metadata extent check for a conservative prior capture charge; no subjects."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
here = root / "experiments/m193c-output-grid"
paths = [p for p in (here / "runtime-capture-1").rglob("*") if p.is_file()]
paths += [here / name for name in (
    "derivative-runtime-1.json", "runtime-capture-release-1.json",
    "runtime-capture.py", "runtime-capture-preregister.md",
    "independent-runtime-capture-review.md", "independent-runtime-capture-release-review.md",
    "independent-runtime-capture-1-read.md",
    "work/runtime-capture-1-console.txt", "work/runtime-capture-1-exit.txt",
    "work/runtime-capture-1-outer.json", "work/prepare-runtime-capture-1.py",
    "work/prepare-runtime-archive-1.py", "work/native-prior-work-1.json",
    "work/native-prior-work-1.md", "work/native-adjacent-dependencies-1.json",
    "work/check-native-prior-reservation-1.py",
)]
rows = []
for path in sorted(set(paths)):
    raw = path.read_bytes()
    rows.append(dict(path=path.relative_to(root).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
record = dict(scope="actual enumerated capture metadata extents, not write I/O",
              reserved_bytes=1 << 20, observed_bytes=sum(row["bytes"] for row in rows), files=rows)
raw = (json.dumps(record, indent=2) + "\n").encode()
assert record["observed_bytes"] + len(raw) < record["reserved_bytes"]
assert not any(p.is_dir() for p in here.glob("native-derivative-*"))
with (here / "work/native-prior-reservation-1.json").open("xb") as stream:
    stream.write(raw)
print(json.dumps(dict(file_count=len(rows), observed_bytes=record["observed_bytes"],
                     check_record_bytes=len(raw), reservation_bytes=1 << 20)))
