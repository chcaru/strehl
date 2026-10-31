"""Packaged-binary compatibility checks; existing captures/caches are read-only.

Runs bounded delivery regressions, not new research or parameter selection.
Each phase and output directory must be fresh. Commands/resources use run-command.py.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "outputs/multi-stack/completion"
DEST = ROOT / "outputs/multi-stack/integration-2026-10-31"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run(command, label, environment):
    runner = [sys.executable, str(ROOT / "experiments/multi-stack-2026-10-28/run-command.py"),
              "--receipt", str(DEST / (label + "-run")), "--cwd", str(ROOT)]
    for key, value in environment.items():
        runner += ["--env", key + "=" + value]
    subprocess.run(runner + ["--"] + command, cwd=ROOT, check=True)


def compare(left, right):
    a, b = tifffile.imread(left), tifffile.imread(right)
    assert a.shape == b.shape and a.dtype == b.dtype, (left, right)
    assert np.isfinite(a).all() and np.isfinite(b).all()
    assert np.array_equal(a.view(np.uint8), b.view(np.uint8)), (left, right)
    return {"left": str(left), "right": str(right), "shape": list(a.shape),
            "dtype": str(a.dtype), "pixel_bits_equal": True,
            "left_sha256": digest(left), "right_sha256": digest(right),
            "pixel_sha256": hashlib.sha256(a.tobytes()).hexdigest()}


def repeat(binary):
    old = json.loads((BASE / "noise-bee-repeat-equal-run-01/receipt.json").read_text())
    results = {}
    for arm in ("export-off", "export-on"):
        command = old["command"].copy()
        command[0] = str(binary)
        command[command.index("--out-dir") + 1] = str(DEST / arm)
        if arm == "export-off":
            command.remove("--contribution-maps")
        run(command, arm, old["environment"])
        report = json.loads((DEST / arm / "render-report.json").read_text())
        results[arm] = {"command": command, "report": report,
                        "sensor_present": (DEST / arm / "sensor-master.tiff").is_file()}
    assert not results["export-off"]["sensor_present"]
    assert results["export-on"]["sensor_present"]
    comparisons = []
    for name in ("photograph.tiff", "master.tiff"):
        comparisons.append(compare(DEST / "export-off" / name, DEST / "export-on" / name))
        comparisons.append(compare(DEST / "export-on" / name,
                                   ROOT / "outputs/multi-stack/overflow/repeat-proposals-17/legacy" / name))
    sensor = tifffile.imread(DEST / "export-on/sensor-master.tiff")
    assert sensor.dtype == np.float32 and sensor.ndim == 2 and np.isfinite(sensor).all()
    save(DEST / "repeat-verification.json", {
        "schema": "strehl.tryout-repeat-verification.v1", "executable_sha256": digest(binary),
        "comparisons": comparisons, "sensor_shape": list(sensor.shape),
        "sensor_dtype": str(sensor.dtype), "sensor_finite": True,
        "sensor_sha256": digest(DEST / "export-on/sensor-master.tiff"),
        "sensor_contract": results["export-on"]["report"].get("native_sensor_master"),
        "commands": {key: value["command"] for key, value in results.items()},
        "scope": "Exact complete output compatibility; no new photographic-quality or noise claim."})


def ordinary(binary):
    old = json.loads((BASE / "ordinary-regression-run-16/receipt.json").read_text())
    command = old["command"].copy()
    command[0] = str(binary)
    output = DEST / "ordinary"
    output.mkdir(exist_ok=False)
    for flag, name in (("--out", "photograph.tiff"), ("--linear-master", "master.tiff"),
                       ("--sensor-master", "sensor.tiff")):
        command[command.index(flag) + 1] = str(output / name)
    # A private copy isolates alignment; keep the already-bound source cache idle.
    warpmap = output / "warpmap.txt"
    shutil.copyfile(BASE / "ordinary-regression-16/warpmap.txt", warpmap)
    environment = old["environment"].copy()
    environment["STREHL_WARPMAP"] = str(warpmap)
    run(command, "ordinary", environment)
    comparisons = [compare(output / name, BASE / "ordinary-regression-16" / name)
                   for name in ("photograph.tiff", "master.tiff", "sensor.tiff")]
    save(DEST / "ordinary-verification.json", {
        "schema": "strehl.tryout-ordinary-verification.v1", "executable_sha256": digest(binary),
        "command": command, "environment": environment, "comparisons": comparisons,
        "scope": "Complete 299-source pixels match product16, whose complete pixels matched the original baseline."})


def package(binary):
    directory = binary.parent
    source = directory / "source"
    manifest = json.loads((source / "desktop-source.json").read_text(encoding="utf-8-sig"))
    seen = set()
    for entry in manifest["files"]:
        path = entry["path"].replace("\\", "/")
        assert path not in seen, path
        seen.add(path)
        assert digest(source / path) == entry["sha256"], path
    with zipfile.ZipFile(directory / "strehl-source.zip") as archive:
        for name in archive.namelist():
            assert not name.lower().endswith((".arw", ".tiff", ".tif", ".cfa", ".exe")), name
    identity = json.loads((directory / "desktop-package.json").read_text(encoding="utf-8-sig"))
    for entry in identity["files"]:
        path = directory / entry["path"]
        assert path.stat().st_size == entry["bytes"] and digest(path) == entry["sha256"], path
    save(DEST / "package-verification.json", {
        "source_commit": "9f81063231b78b9244874ccfa4bb939b60517ef5",
        "build_id": manifest["build_id"], "source_sha256": manifest["source_sha256"],
        "source_files_verified": len(seen), "package_files_verified": len(identity["files"]),
        "no_raw_tiff_or_cfa_data_in_source_zip": True, "files": identity["files"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("repeat", "ordinary", "package"))
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    {"repeat": repeat, "ordinary": ordinary, "package": package}[args.phase](args.binary.resolve(strict=True))
