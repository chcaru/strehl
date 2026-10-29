"""Prepare explicit source plans; copying RAWs requires root's lane release.

Default mode reads the existing preview receipt only. --materialize copies its
34 selected originals into a fresh isolated directory, checks original stamps,
hashes while copying, and verifies the destination bytes. Captures stay read-only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil

GROUPS = ("marigold-3", "marigold-offcenter")

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, default=Path("outputs/multi-stack/completion/mosaic-preview-02/report.json"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--materialize", action="store_true")
    args = parser.parse_args()
    root = args.out.resolve()
    records = json.loads(args.receipt.read_text(encoding="utf-8"))["sources"]
    selected = []
    passes = []
    complete_passes = []
    for pass_index, group in enumerate(GROUPS):
        frames = sorted((r for r in records if r["group"] == group), key=lambda r: r["acquisition_index"])
        assert len(frames) == 17, (group, len(frames))
        source_dirs = list(dict.fromkeys(str(Path(r["path"]).parent) for r in frames))
        copy_dirs = [root / "inputs" / f"pass-{pass_index:02}" / f"segment-{s:02}" for s in range(len(source_dirs))]
        passes.append({"name": group + "-17-commissioning", "directories": [str(p) for p in copy_dirs]})
        complete_passes.append({"name": group, "directories": source_dirs})
        for row in frames:
            source = Path(row["path"])
            segment = source_dirs.index(str(source.parent))
            target = copy_dirs[segment] / f"{row['acquisition_index']:05}-{source.name}"
            assert not root.is_relative_to(source.parent.resolve()), "output is inside a capture directory"
            selected.append({"pass": pass_index, "original_ordinal": row["acquisition_index"], "source": str(source), "copy": str(target), "bytes": row["bytes"], "mtime_ns": row["mtime_ns"], "preview_sha256": row["preview_sha256"]})
    root.mkdir(parents=True, exist_ok=False)
    plan = {"schema": "strehl.mosaic-native-pilot-plan.v1", "materialized": args.materialize, "selection": "17 previously recorded evenly spaced originals from each complete pass; ordered directory segments retained", "scope": "Consumer commissioning only; sparse focus slices cannot certify complete-stack photographic quality", "total_bytes": sum(r["bytes"] for r in selected), "frames": selected}
    if args.materialize:
        for item in selected:
            source, target = Path(item["source"]), Path(item["copy"])
            before = source.stat()
            assert (before.st_size, before.st_mtime_ns) == (item["bytes"], item["mtime_ns"]), source
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".copying")
            h = hashlib.sha256()
            with source.open("rb") as inp, temporary.open("xb") as out:
                for block in iter(lambda: inp.read(1024 * 1024), b""):
                    h.update(block)
                    out.write(block)
            after = source.stat()
            assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns), source
            assert digest(temporary) == h.hexdigest(), target
            temporary.rename(target)
            shutil.copystat(source, target)
            item["source_sha256"] = h.hexdigest()
            item["copy_sha256"] = h.hexdigest()
    for filename, value in [
        ("plan.json", plan),
        ("pilot.json", {"version": 1, "mode": "mosaic", "primary_pass": None, "passes": passes}),
        ("complete-827.json", {"version": 1, "mode": "mosaic", "primary_pass": None, "passes": complete_passes}),
    ]:
        with (root / filename).open("x", encoding="utf-8", newline="\n") as out:
            json.dump(value, out, indent=2)
            out.write("\n")
    print(json.dumps({"out": str(root), "frames": len(selected), "bytes": plan["total_bytes"], "materialized": args.materialize}))

if __name__ == "__main__":
    main()
