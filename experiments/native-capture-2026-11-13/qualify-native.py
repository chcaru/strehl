"""Exercise the native app through its revision-checked control interface.

one-plane exposes exactly one A7CR four-shot group, after refusing an active
sequence or pre-existing bounds. No credentials or RAWs enter this report.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/strehl-control.py"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--session-file", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--action", choices=["inspect", "one-plane", "import", "simulator"], default="inspect")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    base = [sys.executable, str(HELPER), "--exe", str(args.exe), "--session-file", str(args.session_file)]
    events = []

    def control(*command):
        result = subprocess.run([*base, *command], capture_output=True, text=True, timeout=25)
        data = json.loads(result.stdout)
        if result.returncode or data.get("error"):
            raise RuntimeError(data.get("error") or result.stderr)
        return data["data"]

    def snapshot():
        return control("snapshot")["result"]

    def wait(predicate, timeout=40):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = snapshot()
            if predicate(state):
                return state
            time.sleep(0.2)
        raise RuntimeError("Native state wait timed out")

    def command(value):
        state = snapshot()
        request = {"expected_revision": state["revision"], "command": value}
        path = args.out / f"request-{len(events):03}.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        result = control("call", "--request", str(path))
        events.append({"command": value, "reply": result})
        return result

    def camera(op, **fields):
        current = snapshot()["capture"]["state"]
        request = {"id": uuid.uuid4().hex, **{k: current[k] for k in ("camera_revision", "plan_revision", "sequence_id")}, "command": {"op": op, **fields}}
        command({"operation": "capture_command", "request": request})
        state = wait(lambda s: not s["capture"]["pending"])
        if state["capture"].get("command_error"):
            raise RuntimeError(state["capture"]["command_error"])
        return state

    command({"operation": "open_capture"})
    initial = wait(lambda s: s["capture"]["online"])
    if args.action == "simulator" and not initial["capture"]["state"]["connected"]:
        camera("connect")
    initial = wait(lambda s: s["capture"]["preview"])
    (args.out / "initial.json").write_text(json.dumps(initial, indent=2), encoding="utf-8")
    if args.action == "one-plane":
        state = initial["capture"]["state"]
        assert state["phase"] == "ready" and not state["busy"]
        assert state["camera_model"] == "ILCE-7CR" and state["shots_per_plane"] == 4
        assert not state["start_set"] and not state["end_set"], "Preserve the user's prepared bounds"
        original_position = state["position"]
        camera("mark", start=True)
        wait(lambda s: s["capture"]["state"]["start_set"])
        camera("mark", start=False)
        wait(lambda s: s["capture"]["state"]["end_set"])
        before_sequence = snapshot()["capture"]["state"]["sequence_id"]
        camera("start")
        final = wait(lambda s: s["capture"]["state"]["sequence_id"] > before_sequence and s["capture"]["state"]["phase"] in ("complete", "fault"), 60)
        capture = final["capture"]["state"]
        assert capture["phase"] == "complete", capture.get("failure")
        assert capture["completed"] == 1 and capture["position"] == original_position
        assert capture["storage"]["saved_frames"] == 4 and capture["storage"]["pending_frames"] == 0
        latest = Path(capture["storage"]["receipt"]["path"]).parent
        wait(lambda s: any(Path(c["folder"]) == latest for c in s["capture"]["completed"]))
        (args.out / "capture-complete.json").write_text(json.dumps(final, indent=2), encoding="utf-8")
        camera("disconnect")
        wait(lambda s: s["capture"]["state"]["phase"] == "disconnected")
        camera("connect")
        wait(lambda s: s["capture"]["state"]["phase"] == "ready" and not s["capture"]["state"]["start_set"])
    if args.action in ("import", "one-plane"):
        final = wait(lambda s: len(s["capture"]["completed"]) > 0)
        expected = final["capture"]["completed"][0]["frames"]
        command({"operation": "import_capture", "index": 0})
        final = wait(lambda s: s["source_count"] == expected and not s["busy"]["opening"])
        assert final["source_count"] == expected
        (args.out / "imported.json").write_text(json.dumps(final, indent=2), encoding="utf-8")
    if args.action == "simulator":
        assert initial["capture"]["state"]["demo"]
        if not initial["capture"]["state"]["connected"]:
            camera("connect")
        wait(lambda s: s["capture"]["state"]["editable"])
        camera("mark", start=True)
        camera("jog", delta=16)
        wait(lambda s: s["capture"]["state"]["editable"])
        camera("mark", start=False)
        camera("settings", step=1, settle_ms=100, approach=16, capture_timeout_s=120)
        camera("start")
        wait(lambda s: s["capture"]["state"]["phase"] == "capturing")
        camera("pause")
        wait(lambda s: s["capture"]["state"]["phase"] == "paused")
        camera("resume")
        wait(lambda s: s["capture"]["state"]["phase"] == "capturing")
        camera("stop")
        wait(lambda s: s["capture"]["state"]["phase"] == "stopped")
        camera("mark", start=True)
        camera("mark", start=False)
        camera("start")
        wait(lambda s: s["capture"]["state"]["phase"] == "complete")
    (args.out / "events.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
    print(json.dumps({"action": args.action, "outcome": "passed", "commands": len(events)}))


if __name__ == "__main__":
    main()
