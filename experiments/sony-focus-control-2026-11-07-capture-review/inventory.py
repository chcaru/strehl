"""Read-only inventory and log-to-RAW reconciliation for the owner's first two tests."""
import collections
import datetime as dt
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

import rawpy
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
INPUT = Path(r"D:\remote-control-test")
OUT = ROOT / "outputs/sony-focus-control-capture-review"
EXIFTOOL = Path.home() / "AppData/Local/Programs/ExifTool/ExifTool.exe"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    all_files = sorted(p for p in INPUT.rglob("*") if p.is_file())
    metadata_command = [str(EXIFTOOL), "-json", "-n", "-r", "-ext", "ARW",
                        "-FileName", "-Directory", "-DateTimeOriginal", "-SubSecTimeOriginal",
                        "-ExposureTime", "-FNumber", "-ISO", "-WhiteBalance", "-ColorTemperature",
                        "-WB_RGGBLevels", "-FocusPosition2", "-FocusDistance", "-FocusMode",
                        "-DriveMode", "-ImageWidth", "-ImageHeight", "-LensModel", "-Model",
                        "-BlackLevel", "-WhiteLevel", "-RawFileType", "-ImageStabilization",
                        str(INPUT / "DCIM")]
    result = subprocess.run(metadata_command, capture_output=True, text=True, encoding="utf-8", check=True)
    (OUT / "exif.json").write_text(result.stdout, encoding="utf-8")
    metadata = json.loads(result.stdout)
    metadata.sort(key=lambda m: (m["DateTimeOriginal"], str(m.get("SubSecTimeOriginal", "")), m["SourceFile"]))
    records = []
    for index, path in enumerate(all_files):
        info = path.stat()
        records.append({"path": path.relative_to(INPUT).as_posix(), "bytes": info.st_size,
                        "mtime_ns": info.st_mtime_ns, "sha256": sha(path)})
        if index % 25 == 0:
            print(f"Hashed {index + 1}/{len(all_files)} files", flush=True)
    raw_hashes = [r["sha256"] for r in records if r["path"].lower().endswith(".arw")]
    assert len(raw_hashes) == 146 and len(set(raw_hashes)) == 146
    by_relative = {r["path"]: r for r in records}
    sessions = []
    raw_index = 0
    for session_index, path in enumerate(sorted(INPUT.glob("focus-test-*/manifest.json"))):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        assert manifest["state"] == "capture-complete-camera-reported-verify-sd-card"
        assert manifest["restoration"]["restored"] and len(manifest["captures"]) == 57
        events = [json.loads(line) for line in path.with_name("events.jsonl").read_text(encoding="utf-8").splitlines()]
        focus_replies = [e["response"] for e in events if "requested" in e.get("response", {})]
        assert all(r["requested"] == r["readback"] and r["completion"] == "sony-focus-complete" for r in focus_replies)
        frame_records = []
        clock_offset = None
        for capture in manifest["captures"]:
            expected = capture["count"]
            report = capture["camera_report"]
            assert report["destination"] == "memory-card" and report["captured_events"] == expected and report["files"] == []
            for side in ("before", "after"):
                assert capture[side]["properties"]["StillImageStoreDestination"]["value"] == 2
            for member in range(expected):
                raw = metadata[raw_index]
                raw_index += 1
                raw_path = Path(raw["SourceFile"])
                ordinal = len(frame_records) + 1
                # Camera clock is not synchronized to the laptop. Anchor its offset
                # once per run and check every remaining capture's relative timing.
                camera_time = dt.datetime.strptime(raw["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S").replace(
                    tzinfo=dt.timezone(dt.timedelta(hours=-8)))
                log_time = dt.datetime.fromisoformat(capture["utc"])
                delta = (camera_time - log_time).total_seconds()
                if clock_offset is None:
                    clock_offset = delta
                relative_delta = delta - clock_offset
                assert -2 <= relative_delta <= report["elapsed_ms"] / 1000 + 2, (raw_path, relative_delta)
                props = capture["before"]["properties"]
                shutter = props["ShutterSpeed"]["value"]
                assert abs(raw["ExposureTime"] - (shutter >> 16) / (shutter & 65535)) < 1e-8
                assert raw["ISO"] == props["IsoSensitivity"]["value"] == 100
                assert abs(raw["FNumber"] - props["FNumber"]["value"] / 100) < 1e-6
                frame_records.append({"ordinal": ordinal, "path": str(raw_path),
                    "relative_path": raw_path.relative_to(INPUT).as_posix(),
                    "sha256": by_relative[raw_path.relative_to(INPUT).as_posix()]["sha256"],
                    "sequence": capture["sequence"], "phase": capture["phase"],
                    "repeat": capture.get("repeat"), "offset": capture.get("offset"),
                    "approach_side": capture.get("approach_side"), "group_member": member + 1,
                    "focus_readback": props["FocusPositionCurrentValue"]["value"] if expected == 1 else None,
                    "camera_minus_log_s": delta, "relative_to_first_clock_offset_s": relative_delta, "metadata": raw})
        assert len(frame_records) == 73
        overview = []
        for ordinal in (1, 9, 10, 11, 23, 56, 64):
            source = Path(frame_records[ordinal - 1]["path"])
            with rawpy.imread(str(source)) as raw:
                thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                preview = Image.open(io.BytesIO(thumb.data)).convert("RGB")
            else:
                preview = Image.fromarray(thumb.data)
            preview.thumbnail((1400, 1000))
            target = OUT / f"run-{session_index + 1}-image-{ordinal:02d}-orientation.jpg"
            preview.save(target, quality=93)
            overview.append(str(target))
        session = {"name": path.parent.name, "manifest_sha256": sha(path), "base": manifest["base"],
                   "started_utc": manifest["started_utc"], "finished_utc": manifest["finished_utc"],
                   "plan": manifest["plan_summary"], "arguments": manifest["arguments"],
                   "driver_sha256": manifest["driver_sha256"], "script_sha256": manifest["script_sha256"],
                   "sdk_version": manifest["connection"]["sdk_version"],
                   "focus_replies": len(focus_replies), "restoration": manifest["restoration"],
                   "camera_clock_offset_s": clock_offset,
                   "frames": frame_records, "orientation_previews": overview}
        sessions.append(session)
        print(f"Run {session_index + 1}: 73 matching RAWs, {len(focus_replies)} completed focus commands", flush=True)
    assert raw_index == len(metadata)
    inventory = {"input": str(INPUT), "files": records, "sessions": sessions,
                 "metadata_command": metadata_command, "metadata_stderr": result.stderr,
                 "environment": {"host": platform.platform(), "python": sys.version,
                     "workers": 1, "omp_threads": os.environ.get("OMP_NUM_THREADS"),
                     "rawpy": importlib.metadata.version("rawpy"), "libraw": rawpy.libraw_version,
                     "source_sha256": sha(Path(__file__))}}
    (OUT / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(f"Inventory saved: {OUT / 'inventory.json'}", flush=True)


if __name__ == "__main__":
    main()
