#!/usr/bin/env python3
"""Sony a7C II focus control: RAWs stay on the SD card; only logs go to this computer."""
# SPDX-License-Identifier: MIT OR Apache-2.0
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXE = ROOT / "outputs/sony-control/bin/strehl-sony-control.exe"
OFFSETS = [0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64]
SCHEMA = "strehl-sony-focus-v2-card-only"


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def plan_test(base, direction=1, approach=128, positive=512, native=True):
    """All targets are fixed before any camera mutation. Units are NOT micrometres."""
    if direction not in (-1, 1) or approach < 1 or positive <= max(OFFSETS):
        raise ValueError("direction must be +/-1, approach positive, and positive-control offset >64")
    actions = []

    def move(value, phase):
        if not 0 <= value <= 65535:
            raise ValueError(f"Plan crosses the normalized focus range at {value}; refocus away from the endpoint")
        actions.append({"kind": "focus", "phase": phase, "target": value})

    def capture(phase, count=1, **tags):
        actions.append({"kind": "capture", "phase": phase, "count": count, **tags})

    for i in range(5):
        capture("fixed-null", repeat=i)
    for i in range(3):
        move(base, "command-null")
        capture("command-null", repeat=i, offset=0)
    move(base - direction * approach, "positive")
    move(base + direction * positive, "positive")
    capture("positive", offset=direction * positive)
    move(base, "positive-return")
    capture("positive-return", offset=0)
    for repeat in range(3):
        move(base - direction * approach, "fine-sweep")
        for offset in OFFSETS:
            move(base + direction * offset, "fine-sweep")
            capture("fine-sweep", repeat=repeat, offset=direction * offset)
    for repeat in range(3):
        for side in (-1, 1):
            move(base + side * approach, "return-repeatability")
            move(base, "return-repeatability")
            capture("return-repeatability", repeat=repeat, approach_side=side, offset=0)
    if native:
        for repeat in range(2):
            actions.append({"kind": "single", "phase": "native-width-1"})
            move(base - direction * approach, "native-width-1")
            move(base, "native-width-1")
            actions.append({"kind": "native", "phase": "native-width-1", "count": 9})
            capture("native-width-1", count=9, repeat=repeat)
    return actions


def plan_stack(base, step, count):
    if not step or count < 1:
        raise ValueError("Stack needs a nonzero step and positive count")
    end = base + (count - 1) * step
    if not 0 <= min(base, end) <= max(base, end) <= 65535:
        raise ValueError("Stack crosses the normalized focus range; refusing to clamp targets")
    return [action for i in range(count) for action in (
        {"kind": "focus", "phase": "stack", "target": base + i * step},
        {"kind": "capture", "phase": "stack", "count": 1, "plane": i, "offset": i * step},
    )]


def plan_summary(actions):
    counts = collections.Counter()
    for action in actions:
        if action["kind"] == "capture":
            counts[action["phase"]] += action["count"]
    return {"raw_count": sum(counts.values()), "phases": dict(counts), "actions": len(actions)}


class Bridge:
    def __init__(self, executable, log, timeout=90):
        self.log = log
        self.timeout = timeout
        self.pending = False
        self.responses = queue.Queue()
        self.stderr_path = Path(log.name).with_name("native-stderr.log")
        self.stderr = self.stderr_path.open("w", encoding="utf-8")
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        self.process = subprocess.Popen(
            [str(executable), "serve"], cwd=executable.parent,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
            encoding="utf-8", errors="strict", bufsize=1, creationflags=flags,
        )
        threading.Thread(target=self._read, daemon=True).start()
        try:
            self.hello = self._reply(30)
        except BaseException:
            self.close()
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                self.responses.put(json.loads(line))
        except Exception as exc:
            self.responses.put({"ok": False, "error": f"Native protocol read: {exc}"})
        finally:
            self.responses.put({"ok": False, "error": "Native process exited"})

    def record(self, **value):
        self.log.write(json.dumps({"utc": utc(), **value}, ensure_ascii=False) + "\n")
        self.log.flush()

    def _reply(self, timeout):
        try:
            reply = self.responses.get(timeout=timeout)
        except queue.Empty as exc:
            raise RuntimeError("Native helper stopped responding; inspect the camera before restarting") from exc
        self.pending = False
        self.record(response=reply)
        if not reply.get("ok"):
            raise RuntimeError(reply.get("error", "Native command failed"))
        return reply

    def call(self, *parts, timeout=None):
        if self.pending:
            raise RuntimeError("Previous command has no response; refusing another command")
        if any(any(c in str(p) for c in "\t\r\n") for p in parts):
            raise ValueError("Tabs/newlines are not permitted in protocol fields")
        self.record(command=list(parts))
        self.pending = True
        self.process.stdin.write("\t".join(str(p) for p in parts) + "\n")
        self.process.stdin.flush()
        return self._reply(timeout or self.timeout)

    def close(self):
        restoration = {"restored": False, "reason": "Helper unavailable"}
        try:
            if self.process.poll() is None:
                if self.pending:
                    # Ctrl+C stops future exposures, not the active native command.
                    print("Waiting for the active operation before restoring settings...", file=sys.stderr)
                    try:
                        self._reply(self.timeout)
                    except RuntimeError:
                        pass
                if not self.pending:
                    restoration = self.call("quit", timeout=40)
        except Exception as exc:
            restoration = {"restored": False, "reason": str(exc)}
        finally:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=8)
            except (OSError, subprocess.TimeoutExpired):
                self.process.terminate()  # Our helper only; no camera shutter retry.
                self.process.wait(timeout=8)
                restoration = {"restored": False, "reason": "Native helper terminated; inspect camera manually"}
            self.stderr.close()
        return restoration


def value(status, name):
    prop = status["properties"].get(name, {})
    if not prop.get("readable") or prop.get("value") is None:
        raise RuntimeError(f"{name} is unavailable: {prop}")
    return prop["value"]


def preflight(status):
    if value(status, "FocusMode") != 1:
        raise RuntimeError("Set MF and manually focus the target before starting; the initial focus must be stable")
    if value(status, "ExposureProgramMode") != 1:
        raise RuntimeError("Set the camera exposure dial to M before this experiment")
    iso = value(status, "IsoSensitivity")
    if iso & 0xFFFFFF == 0xFFFFFF:
        raise RuntimeError("Choose a fixed ISO; Auto ISO invalidates the comparison")
    if value(status, "ShutterSpeed") == 0:
        raise RuntimeError("Bulb is not supported by this helper")
    base = value(status, "FocusPositionCurrentValue")
    if not isinstance(base, int) or not 0 <= base <= 65535:
        raise RuntimeError("Camera returned an invalid normalized focus value")
    return base


def configure(bridge):
    # SDK enum values, not PTP wire codes. Every setting is read back by the helper.
    bridge.call("set", "StillImageStoreDestination", 2)  # Memory card only, retained on exit
    bridge.call("set", "FocusMode", 1)  # MF
    bridge.call("set", "DriveMode", 1)  # Single
    bridge.call("set", "FileType", 2)  # RAW only
    return bridge.call("status")


def card_preflight(status, raw_count):
    if value(status, "StillImageStoreDestination") != 2:
        raise RuntimeError("SD-card-only saving was not accepted; no exposure taken")
    if value(status, "MediaSLOT1_Status") != 0:
        raise RuntimeError("SD card is missing or unavailable")
    if value(status, "MediaSLOT1_WritingState") != 1:
        raise RuntimeError("SD card is busy or its writing state is unavailable")
    if value(status, "FocusBracketShootingStatus") != 0:
        raise RuntimeError("A native focus bracket is already active")
    if value(status, "MediaSLOT1_RemainingNumber") < raw_count:
        raise RuntimeError(f"SD card reports insufficient space for {raw_count} RAWs")


def configure_native(bridge, count):
    bridge.call("set", "DriveMode", 0x12001)
    # Order must be set first: 0 -> - -> + constrains shot count to three.
    bridge.call("set", "FocusBracketOrder", 2)
    bridge.call("set", "FocusBracketShotNumber", count)
    bridge.call("set", "FocusBracketFocusRange", 1)


def validate_card_capture(reply, count):
    """Validate camera-reported completion, without fetching or reading image files."""
    expected = {"destination": "memory-card", "captured_events": count,
                "card_state": "not-writing", "bracket_idle": True,
                "completion": "camera-events-and-card-idle", "file_verification": "not-performed",
                "files": []}
    for key, required in expected.items():
        if key not in reply or reply[key] != required:
            raise RuntimeError(f"SD-card completion mismatch for {key}: {reply.get(key)!r}")


def execute(bridge, actions, out, settle_ms, timeout, manifest):
    sequence = 0
    image_number = 1
    last_focus = None
    for action in actions:
        kind = action["kind"]
        if kind == "focus":
            last_focus = bridge.call("focus", action["target"], settle_ms, timeout=settle_ms / 1000 + 20)
        elif kind == "single":
            bridge.call("set", "DriveMode", 1)
        elif kind == "native":
            configure_native(bridge, action["count"])
        elif kind == "capture":
            sequence += 1
            image_range = [image_number, image_number + action["count"] - 1]
            print(f"Capture {sequence}: {action['phase']} ({action['count']} RAW to SD card)", flush=True)
            before = bridge.call("status")
            # Persist intent before S2 so partial/uncertain captures can be reconciled on the card.
            record = {**action, "sequence": sequence, "image_range": image_range,
                      "utc": utc(), "focus_command": last_focus, "before": before}
            manifest["active_capture"] = record
            write_json(out / "manifest.json", manifest)
            reply = bridge.call("capture", action["count"], timeout, timeout=timeout + 10)
            validate_card_capture(reply, action["count"])
            record = {**record, "camera_report": reply}
            manifest["captures"].append(record)
            manifest.pop("active_capture")
            write_json(out / "manifest.json", manifest)
            record["after"] = bridge.call("status")
            write_json(out / "manifest.json", manifest)
            image_number += action["count"]
    return sequence


def run(args):
    executable = args.exe.resolve()
    if not executable.is_file():
        raise RuntimeError(f"Build the native helper first: {executable}")
    if args.command == "list":
        result = subprocess.run([str(executable), "list"], cwd=executable.parent, timeout=20)
        if result.returncode:
            raise RuntimeError(f"Camera enumeration failed (exit {result.returncode})")
        return
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": SCHEMA, "started_utc": utc(), "state": "starting", "captures": [],
                "capture_destination": "memory-card", "image_file_verification": "not-performed",
                "arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                "host": platform.platform(), "python": sys.version, "worker_count": 1,
                "driver_sha256": digest(executable), "script_sha256": digest(__file__),
                "optical_precision": "UNVERIFIED; normalized values are not lens motor steps"}
    receipt = executable.parent.parent / "build-receipt.json"
    if receipt.is_file():
        manifest["build"] = json.loads(receipt.read_text(encoding="utf-8"))
    write_json(out / "manifest.json", manifest)
    bridge = None
    failure = None
    with (out / "events.jsonl").open("w", encoding="utf-8", buffering=1) as log:
        try:
            bridge = Bridge(executable, log, timeout=args.timeout + 15)
            manifest["connection"] = bridge.hello
            initial = bridge.call("status")
            manifest["initial"] = initial
            write_json(out / "preflight.json", initial)
            if args.command == "status":
                print(json.dumps(initial, indent=2))
                manifest["state"] = "status-only"
            else:
                if bridge.hello.get("capture_protocol") != 2 or bridge.hello.get("capture_destination") != "memory-card":
                    raise RuntimeError("Native helper is not the SD-card-only version; replace the complete package")
                base = preflight(initial)
                if args.command == "focus-test":
                    actions = plan_test(base, args.direction, args.approach, args.positive, not args.skip_native)
                else:
                    actions = plan_stack(base, args.step, args.count)
                summary = plan_summary(actions)
                manifest.update(base=base, plan=actions, plan_summary=summary)
                write_json(out / "manifest.json", manifest)
                manifest["configured"] = configure(bridge)
                card_preflight(manifest["configured"], summary["raw_count"])
                focus_property = manifest["configured"]["properties"].get("FocusPositionSetting", {})
                if not focus_property.get("writable"):
                    raise RuntimeError("Absolute focus is not writable with this camera/lens/teleconverter state")
                if args.command == "focus-test" and not args.skip_native:
                    configure_native(bridge, 9)
                    bridge.call("set", "DriveMode", 1)
                    manifest["native_preflight"] = "settings accepted; actual burst remains unverified"
                manifest["state"] = "capturing"
                write_json(out / "manifest.json", manifest)
                print(json.dumps(summary), flush=True)
                execute(bridge, actions, out, args.settle_ms, args.timeout, manifest)
                manifest["state"] = "capture-complete-camera-reported-verify-sd-card"
        except BaseException as exc:
            manifest["state"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
            manifest["error"] = str(exc) or type(exc).__name__
            failure = exc
        finally:
            if bridge:
                manifest["restoration"] = bridge.close()
                if not manifest["restoration"].get("restored"):
                    print("Settings were not fully restored; inspect manifest.json and the camera.", file=sys.stderr)
                    if failure is None:
                        failure = RuntimeError("Capture finished but camera restoration is incomplete")
                        manifest["state"] = "restoration-incomplete"
            manifest["finished_utc"] = utc()
            write_json(out / "manifest.json", manifest)
    print(f"Session: {out}", flush=True)
    if failure is not None:
        raise failure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="Enumerate only; no exposure or focus changes")
    plan = commands.add_parser("plan", help="Print the fixed test plan without connecting")
    plan.add_argument("--base", type=int, default=32768, help="Illustrative normalized value")
    plan.add_argument("--direction", type=int, choices=[-1, 1], default=1)
    plan.add_argument("--approach", type=int, default=128)
    plan.add_argument("--positive", type=int, default=512)
    plan.add_argument("--skip-native", action="store_true")
    for name in ("status", "focus-test", "stack"):
        p = commands.add_parser(name)
        p.add_argument("--out", type=Path, required=True, help="New log directory; photos stay on the SD card")
        p.add_argument("--timeout", type=int, default=90, help="Capture/card-ready timeout per shot or group in seconds")
        if name != "status":
            p.add_argument("--settle-ms", type=int, default=1000)
        if name == "focus-test":
            p.add_argument("--direction", type=int, choices=[-1, 1], default=1)
            p.add_argument("--approach", type=int, default=128)
            p.add_argument("--positive", type=int, default=512)
            p.add_argument("--skip-native", action="store_true", help="Diagnose absolute focus only; cannot establish improvement over native width 1")
        if name == "stack":
            p.add_argument("--step", type=int, required=True, help="Signed normalized increment; requires optical calibration")
            p.add_argument("--count", type=int, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        actions = plan_test(args.base, args.direction, args.approach, args.positive, not args.skip_native)
        print(json.dumps({"summary": plan_summary(actions), "plan": actions}, indent=2))
        return
    if args.command != "list" and not 5 <= args.timeout <= 3600:
        parser.error("timeout must be 5..3600 seconds")
    if hasattr(args, "settle_ms") and not 100 <= args.settle_ms <= 30000:
        parser.error("settle-ms must be 100..30000")
    run(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped. Photos remain on the SD card; logs remain in the session directory.", file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
