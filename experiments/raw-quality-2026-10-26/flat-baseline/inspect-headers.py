"""Bind three native optical-header observations without decoding RAW pixels."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path("D:/personal/macro/requests/misc-diagnostic/high-res-calibration-slide-cpl/flat-sw4-cpl/flat-et1s-sw4-cpl")
OUT = ROOT / "outputs/raw-quality-2026-10-26/flat-1s-metadata"
EXE = ROOT / "outputs/raw-quality-2026-10-26/baseline-strehl.exe"


def bind(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(1 << 20):
            h.update(block)
    stat = path.stat()
    return dict(path=str(path), bytes=stat.st_size, mtime_ns=stat.st_mtime_ns, sha256=h.hexdigest())


def main():
    start = time.monotonic()
    files = sorted((p for p in SOURCE.iterdir() if p.is_file() and p.suffix.lower() == ".arw"), key=str)
    assert len(files) == 60 and not OUT.exists()
    inventory = [(p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in files]
    executable = bind(EXE)
    assert executable["sha256"] == "89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388"
    OUT.mkdir()
    records = []
    for index in (0, 30, 59):
        source = files[index]
        before = bind(source)
        target = OUT / f"source{index:03d}-optical.json"
        command = [str(EXE), "focus", "inspect", str(source), "--optical", "--out", str(target)]
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
        (OUT / f"source{index:03d}-process.log").write_text(process.stdout + process.stderr, encoding="utf-8")
        assert process.returncode == 0, process.stderr
        json.loads(target.read_text())
        assert bind(source) == before
        records.append(dict(index=index, source=before, command=command, exit_code=process.returncode,
                            output=bind(target), source_unchanged=True))
    assert [(p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in files] == inventory
    assert bind(EXE) == executable
    result = dict(status="THREE_NATIVE_HEADERS_RECORDED", frames=60, executable=executable, command=sys.argv,
                  records=records, inventory=inventory, seconds=time.monotonic() - start,
                  scope="Header inspection plus original-byte hashing; no pixel decoder, fit or quality claim.")
    with (OUT / "receipt.json").open("x", encoding="utf-8", newline="\n") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print(json.dumps({"status": result["status"], "seconds": result["seconds"], "files": [r["source"]["path"] for r in records]}))


if __name__ == "__main__":
    main()
