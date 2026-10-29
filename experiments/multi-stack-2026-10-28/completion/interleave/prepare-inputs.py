"""Create byte-verified even/odd source copies; never modify capture roots."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sys
import time

root = Path(__file__).resolve().parents[4]
inventory_path = root / "experiments/multi-stack-2026-10-28/corpus/inventory.json"
inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
capture = next(item for item in inventory["brackets"] if item["id"] == "b14")
source = Path(capture["directory"]).resolve(strict=True)
destination = root / "outputs/multi-stack/completion/interleave-inputs"
destination.mkdir(parents=True, exist_ok=False)
for name in ("even", "odd"):
    (destination / name).mkdir()
paths = sorted(p for p in source.iterdir() if p.suffix.lower() == ".arw")
assert len(paths) == capture["count"] == 182
started = time.time()

def copy_one(item):
    ordinal, original = item
    before = original.stat()
    target = destination / ("even" if ordinal % 2 == 0 else "odd") / original.name
    digest = hashlib.sha256()
    with original.open("rb") as reader, target.open("xb") as writer:
        while block := reader.read(1024 * 1024):
            digest.update(block)
            writer.write(block)
        writer.flush()
        os.fsync(writer.fileno())
    after = original.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    with target.open("rb") as reader:
        check = hashlib.file_digest(reader, "sha256").hexdigest()
    assert digest.hexdigest() == check
    os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
    return {"ordinal": ordinal, "original": str(original), "copy": str(target),
            "bytes": before.st_size, "mtime_ns": before.st_mtime_ns, "sha256": check}

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    copies = list(pool.map(copy_one, enumerate(paths)))
assert len({item["sha256"] for item in copies}) == len(copies)
assert sorted(p for p in source.iterdir() if p.suffix.lower() == ".arw") == paths
for name, mode, passes in (
    ("interleave", "interleave", [("Even focus positions", destination / "even"), ("Odd focus positions", destination / "odd")]),
    ("dense", "combine", [("Dense original sweep", source)]),
):
    manifest = {"version": 1, "mode": mode, "primary_pass": None,
                "passes": [{"name": label, "directories": [str(path)]} for label, path in passes]}
    (destination / f"{name}.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
receipt = {"schema": "strehl.interleave-inputs.v1", "workers": 4,
           "command": sys.argv, "source": str(source), "copies": copies,
           "elapsed_seconds": time.time() - started, "total_bytes": sum(c["bytes"] for c in copies),
           "raw_decodes": 0, "capture_modifications": 0}
(destination / "preparation.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in receipt.items() if k != "copies"}, indent=2))
