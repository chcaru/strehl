"""Exercise the delivered GUI through its local API, then native offscreen GPU.

Imports only a completed output grant; no RAW folder is granted or decoded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/strehl-control.py"
DEST = ROOT / "outputs/multi-stack/integration-2026-10-31"


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def verify(binary):
    state = DEST / "ui"
    state.mkdir(exist_ok=False)
    pointer, catalog = state / "ready.json", state / "catalog.json"
    count = 0

    def call(tail, session=True):
        nonlocal count
        count += 1
        command = [sys.executable, str(HELPER), "--exe", str(binary)]
        if session:
            command += ["--session-file", str(pointer)]
        command += tail
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", timeout=100)
        save(state / f"{count:03}-command.json", {"command": command, "exit_code": result.returncode,
                                               "stdout": result.stdout, "stderr": result.stderr})
        assert result.returncode == 0, (command, result.stdout, result.stderr)
        return json.loads(result.stdout)

    def snapshot():
        return call(["snapshot"])["data"]["result"]

    launcher_log = (state / "launcher.log").open("w", encoding="utf-8")
    launcher = subprocess.Popen([sys.executable, str(HELPER), "--exe", str(binary),
                                "--session-file", str(pointer), "launch", "--wait",
                                "--grant", str(DEST), "--catalog", str(catalog),
                                "--output-dir", str(state / "outputs")], cwd=ROOT,
                               stdout=launcher_log, stderr=subprocess.STDOUT)
    published = False
    try:
        deadline = time.monotonic() + 35
        while not pointer.is_file() and time.monotonic() < deadline:
            assert launcher.poll() is None, "Owned UI launch failed; inspect launcher.log"
            time.sleep(.2)
        assert pointer.is_file(), "UI publication timed out"
        published = True
        initial = snapshot()
        assert len(initial["grants"]) == 1
        request = state / "import-request.json"
        save(request, {"expected_revision": initial["revision"], "command": {
            "operation": "import_completed_session", "grant_id": initial["grants"][0]["id"],
            "relative_path": "export-on", "parent_id": None}})
        call(["call", "--request", str(request)])
        deadline = time.monotonic() + 120
        while True:
            current = snapshot()
            if not any(current["busy"].values()):
                assert current["error"] is None, current["error"]
                if current["photo_ready"]:
                    break
            assert time.monotonic() < deadline, "Completed import did not finish"
            time.sleep(1)
        assert current["imported_session"]["renderer_bound"]
        assert not current["imported_session"]["diagnostic_warnings"]
        assert current["session"]["mode"] == "repeat"
        assert current["session"]["primary_pass"] is None
        assert current["session"]["contribution_maps"]
        save(state / "imported-snapshot.json", current)
        call(["shutdown"])
        published = False
        assert launcher.wait(timeout=30) == 0
    finally:
        if published and launcher.poll() is None:
            call(["shutdown"])
            assert launcher.wait(timeout=30) == 0
        launcher_log.close()

    # This process reloads the persisted run and paints the actual egui/wgpu UI.
    screenshot = call(["screenshot", "--open-run", str(DEST / "export-on"),
                       "--catalog", str(catalog), "--png", str(state / "reopened.png"),
                       "--size", "1440x940"], session=False)
    assert screenshot["data"]["state"] == "screenshot_saved"
    assert screenshot["data"]["exit_code"] == 0
    save(state / "verification.json", {"renderer_bound_import": True,
        "diagnostic_warnings": [], "persisted_reopen": True, "owned_headless_exit": 0,
        "completed_output_grant_only": True, "actual_gpu_screenshot": screenshot,
        "visual_review_required": True,
        "scope": "Product import/reopen and rendering, not a new photographic-quality conclusion."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    verify(parser.parse_args().binary.resolve(strict=True))
