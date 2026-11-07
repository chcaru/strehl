#!/usr/bin/env python3
"""Portable launchers: resolve every path relative to the extracted package."""
# SPDX-License-Identifier: MIT OR Apache-2.0
import datetime as dt
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "tools/sony-control/sony-control.py"
PYTHON = [sys.executable, "-I", "-X", "utf8", "-u"]


def run(arguments):
    # Inherit the console so Ctrl+C reaches the controller as KeyboardInterrupt.
    # Its Bridge already isolates the native helper in a separate process group.
    process = subprocess.Popen(PYTHON + [str(CONTROLLER)] + arguments, cwd=ROOT)
    while True:
        try:
            return process.wait()
        except KeyboardInterrupt:
            # Do not forward a second signal: the controller received this one.
            print("Stopping after the active operation; keep this window open.", flush=True)


def session_path(kind):
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return ROOT / "logs" / f"{kind}-{stamp}-{uuid.uuid4().hex[:8]}"


def main():
    mode, *extra = sys.argv[1:] or ["help"]
    if mode == "check":
        print("Camera check only: no focus movement or photographs.\n", flush=True)
        result = run(["list"])
        if result:
            return result
        return run(["status", "--out", str(session_path("preflight")), *extra])
    if mode == "test":
        print("Starting the 73-RAW focus test. The lens will move.\n"
              "Photos are saved only to the SD card; this laptop saves logs.\n"
              "Use the prepared stationary target, MF and manual exposure.\n"
              "Press Ctrl+C once to stop future shots.\n", flush=True)
        return run(["focus-test", "--out", str(session_path("focus-test")), *extra])
    if mode == "offline":
        native = ROOT / "outputs/sony-control/bin/strehl-sony-control.exe"
        result = subprocess.call([str(native), "self-test"], cwd=native.parent)
        if result:
            return result
        return subprocess.call(PYTHON + [str(ROOT / "tools/sony-control/test-sony-control.py")], cwd=ROOT)
    if mode == "cli":
        return run(extra or ["--help"])
    print("Use 01-check-camera.cmd, 02-run-focus-test.cmd or sony-control.cmd --help.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
