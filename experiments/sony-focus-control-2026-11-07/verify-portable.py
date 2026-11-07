"""Verify an extracted SD-only package without requesting photographs or focus moves."""
# SPDX-License-Identifier: MIT OR Apache-2.0
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from zipfile import ZipFile


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--extract-to", type=Path, required=True, help="Fresh directory, preferably containing spaces")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    archive_path = args.zip.resolve()
    extraction = args.extract_to.resolve()
    extraction.mkdir(parents=True, exist_ok=False)
    with ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC failure")
        roots = set()
        for info in archive.infolist():
            name = PurePosixPath(info.filename.replace("\\", "/"))
            if name.is_absolute() or ".." in name.parts or ":" in str(name):
                raise RuntimeError("Unsafe ZIP member")
            roots.add(name.parts[0])
        if len(roots) != 1:
            raise RuntimeError("Expected one package root")
        archive.extractall(extraction)
    package = extraction / roots.pop()
    manifest = json.loads((package / "package-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("capture_destination") != "memory-card" or manifest.get("host_image_downloads") is not False:
        raise RuntimeError("Package is not marked SD-card-only")
    for item in manifest["files"]:
        path = package / item["path"]
        if not path.resolve().is_relative_to(package) or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise RuntimeError(f"Payload integrity failure: {item['path']}")
    actual = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()}
    if actual != {item["path"] for item in manifest["files"]} | {"package-manifest.json"}:
        raise RuntimeError("Unexpected payload files")

    # The developer's installed Python/SDK/PATH cannot satisfy a missing package dependency.
    env = os.environ.copy()
    env["PATH"] = str(Path(env["SYSTEMROOT"]) / "System32")
    env["PYTHONHOME"] = str(extraction / "intentionally missing python home")
    env["PYTHONPATH"] = str(extraction / "intentionally missing python path")
    env["STREHL_NO_PAUSE"] = "1"
    command_shell = env.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
    report = {"archive": str(archive_path), "sha256": digest(archive_path),
              "verified_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "relocated_package": str(package), "payload_files_verified": len(manifest["files"]),
              "environment": {k: env[k] for k in ("PATH", "PYTHONHOME", "PYTHONPATH", "STREHL_NO_PAUSE")},
              "camera_exposures_requested": 0, "checks": []}

    def run(command, expected):
        result = subprocess.run(command, cwd=extraction, env=env, capture_output=True,
                                text=True, encoding="utf-8", errors="strict", timeout=60)
        report["checks"].append({"command": command, "expected_exit": expected, "exit": result.returncode,
                                 "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode not in expected:
            raise RuntimeError(f"Unexpected exit {result.returncode}: {command}\n{result.stderr}")
        return result

    def launcher(name, *extra, expected=(0,)):
        return run([command_shell, "/d", "/c", str(package / name), *extra], list(expected))

    try:
        run([str(package / "runtime/python/python.exe"), "-I", "-c",
             "import sys; print(sys.version); print(sys.executable)"], [0])
        plan = launcher("sony-control.cmd", "plan")
        if json.loads(plan.stdout)["summary"]["raw_count"] != 73:
            raise RuntimeError("Wrong plan")
        offline = launcher("03-offline-check.cmd")
        if '"assertions":19' not in offline.stdout or "Ran 17 tests" not in offline.stderr:
            raise RuntimeError("Offline checks did not exercise both native and Python suites")
        help_result = launcher("02-run-focus-test.cmd", "--help")
        if "--destination" in help_result.stdout:
            raise RuntimeError("Obsolete host-save option is still exposed")
        # Relative --out avoids cmd.exe's /c outer-quote ambiguity in this test
        # harness. The portable launcher itself passes its absolute log path directly to Python.
        launcher("sony-control.cmd", "focus-test", "--out", "must-not-exist",
                 "--destination", "host", expected=(2,))
        if (package / "must-not-exist").exists() or (extraction / "must-not-exist").exists():
            raise RuntimeError("Rejected host-save invocation started a session")
        check = launcher("01-check-camera.cmd", expected=(0, 1))
        if check.returncode == 1 and "found 0" not in check.stderr:
            raise RuntimeError("Camera check failed for a reason other than no connected camera")
        preflights = list((package / "logs").glob("preflight-*/manifest.json"))
        if len(preflights) != 1:
            raise RuntimeError("Expected exactly one read-only check session")
        session = json.loads(preflights[0].read_text(encoding="utf-8"))
        if session["captures"] or session["schema"] != "strehl-sony-focus-v2-card-only":
            raise RuntimeError("Incorrect read-only session manifest")
        if list((package / "logs").glob("focus-test-*")):
            raise RuntimeError("Help unexpectedly created a capture session")
        photos = [str(p) for p in package.rglob("*") if p.suffix.lower() in (".arw", ".jpg", ".jpeg", ".hif")]
        if photos:
            raise RuntimeError(f"Unexpected image files: {photos}")
        report.update(result="passed", photo_files_created=0, preflight_state=session["state"])
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.report.resolve()), "result": report["result"],
                      "payload_files_verified": report["payload_files_verified"], "checks": len(report["checks"])}, indent=2))


if __name__ == "__main__":
    main()
