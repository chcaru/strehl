"""Read-only package/symbol audit. No vendor source is copied into tracked files."""
import hashlib
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

root = Path(__file__).resolve().parents[2]
downloads = Path.home() / "Downloads"
sdk = downloads / "CrSDK_v2.02.00_20260610a_Win64.zip"
command = downloads / "CameraRemoteCommand-2.02.00.zip"
report = {"archives": {}, "sdk_samples": {}, "pattern": "pixel[ _-]?shift"}
for path in (sdk, command):
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    with ZipFile(path) as archive:
        report["archives"][path.name] = {"sha256": sha, "members": archive.namelist()}
with ZipFile(sdk) as archive:
    for sample in ("SimpleCli.zip", "RemoteCli.zip"):
        with ZipFile(io.BytesIO(archive.read(sample))) as files:
            scanned, matches = [], []
            for entry in files.infolist():
                if Path(entry.filename).suffix.lower() in (".h", ".hpp", ".cpp", ".cc"):
                    scanned.append(entry.filename)
                    if re.search(rb"pixel[ _-]?shift", files.read(entry), flags=re.I):
                        matches.append(entry.filename)
            report["sdk_samples"][sample] = {"source_files_scanned": len(scanned), "matching_files": matches}
destination = root / "outputs/sony-control/toolkit-audit.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"archive_hashes": {k: v["sha256"] for k, v in report["archives"].items()},
                  "sdk_samples": report["sdk_samples"], "report": str(destination)}, indent=2))
