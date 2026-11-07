"""Replay the reported seven-pass refusal through the packaged UI's local API.

No eligibility override or successful image render is intended. Capture inputs
remain read-only; all state, logs and request snapshots stay in the task output.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "outputs/multi-stack/shutter-error-fix"
SPEC = importlib.util.spec_from_file_location("controls", ROOT / "experiments/multi-stack-2026-10-28/completion/review/ui-completion-controls.py")
CONTROLS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROLS)


def main(binary):
    state = BASE / "ui"
    state.mkdir(exist_ok=False)
    pointer = state / "ready.json"
    ctl = CONTROLS.Control(SimpleNamespace(exe=binary, session_file=pointer, evidence=state / "commands"))
    log = (state / "launcher.log").open("w", encoding="utf-8")
    launcher = subprocess.Popen([sys.executable, str(ROOT / "scripts/strehl-control.py"),
        "--exe", str(binary), "--session-file", str(pointer), "launch", "--wait",
        "--grant", "D:/personal/macro/insects/bug-3", "--catalog", str(state / "catalog.json"),
        "--output-dir", str(state / "outputs")], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    ready = False
    try:
        deadline = time.monotonic() + 35
        while not pointer.is_file():
            assert launcher.poll() is None and time.monotonic() < deadline
            time.sleep(.2)
        ready = True
        initial = ctl.idle()
        assert len(initial["grants"]) == 1
        grant = initial["grants"][0]["id"]
        passes = []
        for folder in ["107MSDCF", "106MSDCF", "105MSDCF", "104MSDCF", "103MSDCF", "102MSDCF", "100MSDCF"]:
            ctl.mutate({"operation": "import_stack", "grant_id": grant,
                        "relative_path": folder, "name": folder, "parent_id": None})
            current = ctl.idle()
            assert current["error"] is None, current["error"]
            passes.append({"name": folder, "stack_ids": [current["active_stack"]]})
        ctl.mutate({"operation": "create_session", "name": "Reported seven-pass shutter refusal",
                    "passes": passes, "mode": "combine", "primary_pass": 0, "memory_limit_gib": 48})
        current = ctl.idle()
        assert current["error"] is None, current["error"]
        assert current["source_count"] == 1650, current["source_count"]
        ctl.mutate({"operation": "start_stack"})
        current = ctl.wait(lambda s: not s["busy"]["stack"] and s["error"] is not None, seconds=180)
        assert "different shutter times" in current["error"], current["error"]
        assert "Exposure range or Aligned layers" in current["error"]
        assert "full output:" in current["error"]
        assert not current["photo_ready"]
        CONTROLS.write(state / "verification.json", {"exact_pass_order": passes,
            "mode": "combine", "primary": 0, "sources": current["source_count"],
            "displayed_error": current["error"], "actual_packaged_worker": True,
            "no_completed_photograph": True, "scope": "Expected real incompatibility is explained; automatic heterogeneous fusion remains unimplemented."})
        ctl.run(["shutdown"])
        ready = False
        assert launcher.wait(timeout=30) == 0
    finally:
        if ready and launcher.poll() is None:
            ctl.run(["shutdown"])
            assert launcher.wait(timeout=30) == 0
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    main(parser.parse_args().binary.resolve(strict=True))
