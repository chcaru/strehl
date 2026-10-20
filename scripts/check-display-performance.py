"""Measure native Windows photo-pan CPU work using an instrumented Strehl binary.

Example (each run needs a new output directory):
  python scripts/check-display-performance.py --binary path/to/Strehl.exe \
    --run path/to/saved-run --catalog path/to/projects.json --output path/to/a1

Run baseline/current/current/baseline on the same machine without concurrent
builds. Compare each arm's minimum and spread. This is a paced MCP interaction
trace, not a pointer-event benchmark, GPU timing, FPS, or input-to-photon latency.
The binary must expose the per-egui-frame `frame_performance` snapshot contract.
Opening follows file copies, so its timings must not be called cold-start times.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import queue
import shutil
import subprocess
import threading
import time


def digest(path):
    if not path.exists():
        return None
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def remap_paths(value, old, new):
    """Only replace the selected run or its children, never substring matches."""
    if isinstance(value, dict):
        return {key: remap_paths(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [remap_paths(item, old, new) for item in value]
    if isinstance(value, str):
        try:
            path = Path(value)
            if path.is_absolute():
                return str(new / path.resolve().relative_to(old))
        except (OSError, ValueError):
            pass
    return value


class FrameTrace:
    def __init__(self):
        self.rows = {}

    def add(self, snapshot):
        observations = snapshot["frame_performance"]
        if observations["columns"] != ["frame", "update_ms", "previous_frame_cpu_ms"]:
            raise RuntimeError("Binary has an incompatible frame observation contract")
        if "One observation per egui frame" not in observations.get("meaning", ""):
            raise RuntimeError("Binary must group repeated layout passes by egui frame")
        for row in observations["samples"]:
            if len(row) != 3 or not all(math.isfinite(value) for value in row):
                raise RuntimeError("Invalid frame observation")
            frame = int(row[0])
            if row[0] != frame or frame < 0 or row[1] < 0:
                raise RuntimeError("Invalid frame observation")
            previous = self.rows.get(frame)
            # A snapshot can precede a repeated layout pass. Retain the largest
            # accumulated update, and do not count that frame a second time.
            if previous is None or row[1] >= previous[1]:
                self.rows[frame] = list(row)

    @property
    def latest(self):
        if not self.rows:
            raise RuntimeError("The binary has not published any frame observations")
        return max(self.rows)

    def summarize(self, first, last, require_contiguous=True):
        missing = [frame for frame in range(first, last + 2) if frame not in self.rows]
        if require_contiguous and missing:
            raise RuntimeError(f"Frame coverage incomplete; missing IDs: {missing[:12]}")
        samples = []
        for frame in range(first, last + 1):
            row, following = self.rows.get(frame), self.rows.get(frame + 1)
            if row is not None and following is not None and following[2] >= 0:
                # eframe reports the preceding frame's CPU work, including
                # renderer submission. Attribute it to that preceding ID.
                samples.append([frame, row[1], following[2]])
        if not samples:
            raise RuntimeError("No complete frame/previous-CPU pairs were observed")
        if require_contiguous and len(samples) != last - first + 1:
            raise RuntimeError("Framework CPU unavailable for part of the measurement window")

        def column(index):
            values = sorted(row[index] for row in samples)
            return {
                "p50_ms": values[(len(values) - 1) // 2],
                "p95_ms": values[math.ceil((len(values) - 1) * 0.95)],
                "max_ms": values[-1],
            }

        return {
            "frames": len(samples),
            "first_frame": first,
            "last_frame": last,
            "missing_frame_ids": missing,
            "unavailable_cpu_frames": last - first + 1 - len(samples),
            "update": column(1),
            "framework_cpu": column(2),
            "update_sum_ms": sum(row[1] for row in samples),
            "framework_cpu_sum_ms": sum(row[2] for row in samples),
            "columns": ["frame", "update_ms", "framework_cpu_ms"],
            "samples": samples,
        }


def checked_aperture(snapshot, center, zoom):
    """Verify the painted viewport, not merely acceptance of a SetView command."""
    photo_view = snapshot.get("photo_view")
    if not photo_view or "uv" not in photo_view:
        raise ValueError("No painted process photograph is visible")
    uv = photo_view["uv"]
    if len(uv) != 2 or any(len(point) != 2 for point in uv):
        raise ValueError("Invalid painted-photo aperture")
    half = 0.5 / zoom
    expected = [[coordinate - half for coordinate in center],
                [coordinate + half for coordinate in center]]
    if any(not math.isfinite(value) or abs(value - wanted) > 0.002
           for point, target in zip(uv, expected)
           for value, wanted in zip(point, target)):
        raise ValueError(f"Painted aperture {uv} does not match requested {expected}")
    return uv


class Session:
    def __init__(self, process, trace):
        self.process = process
        self.trace = trace
        self.replies = queue.Queue()
        self.counter = 0
        threading.Thread(target=self.pump, daemon=True).start()

    def pump(self):
        try:
            for line in self.process.stdout:
                self.replies.put(json.loads(line))
            self.replies.put(RuntimeError("MCP process closed its output"))
        except Exception as error:
            self.replies.put(error)

    def rpc(self, method, params=None, notification=False):
        self.counter += 1
        value = {"jsonrpc": "2.0", "method": method}
        if not notification:
            value["id"] = self.counter
        if params is not None:
            value["params"] = params
        self.process.stdin.write(json.dumps(value) + "\n")
        self.process.stdin.flush()
        if notification:
            return None
        deadline = time.monotonic() + 60
        while True:
            reply = self.replies.get(timeout=max(0.01, deadline - time.monotonic()))
            if isinstance(reply, Exception):
                raise reply
            if "id" not in reply:
                if time.monotonic() >= deadline:
                    raise TimeoutError("MCP reply timed out")
                continue
            if reply.get("id") != self.counter or "error" in reply:
                raise RuntimeError(f"Unexpected MCP reply: {reply}")
            return reply["result"]

    def tool(self, name, arguments):
        result = self.rpc("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(f"MCP tool failed: {result}")
        return result

    def snapshot(self):
        value = self.tool("strehl_snapshot", {})["structuredContent"]
        current = value.get("result", value)
        self.trace.add(current)
        if current.get("error"):
            raise RuntimeError(f"Native application reported: {current['error']}")
        return current

    def view(self, center, zoom):
        current = self.snapshot()
        return self.tool("strehl_command", {
            "expected_revision": current["revision"],
            "command": {"operation": "set_view", "center": center, "zoom": zoom},
        })

    def settle(self, minimum=1.0, timeout=120):
        started = time.monotonic()
        while time.monotonic() - started < timeout:
            current = self.snapshot()
            display = current.get("display")
            if (current["photo_ready"] and not current["busy"]["opening"]
                    and not current["busy"].get("photo", False)
                    and time.monotonic() - started >= minimum
                    and (display is None or display.get("settled"))):
                return current
            time.sleep(0.12)
        raise TimeoutError("Photo did not settle; inspect native-app.log")

    def drain_after(self, frame):
        deadline = time.monotonic() + 15
        while self.trace.latest <= frame and time.monotonic() < deadline:
            self.snapshot()
            time.sleep(0.02)
        if self.trace.latest <= frame:
            raise TimeoutError("No trailing frame for delayed framework CPU observation")

    def wait_view(self, center, zoom):
        deadline = time.monotonic() + 5
        error = None
        while time.monotonic() < deadline:
            current = self.snapshot()
            try:
                return checked_aperture(current, center, zoom)
            except ValueError as pending:
                error = pending
            time.sleep(0.02)
        raise RuntimeError(f"SetView failed to move the painted photograph: {error}")


def prepare_fixture(run, catalog_path, output):
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    matching = [
        item for item in catalog["runs"] if Path(item["directory"]).resolve() == run
    ]
    if len(matching) != 1:
        raise ValueError("Catalog must contain exactly one record for --run")
    record = matching[0]
    required = {Path(record[key]).resolve() for key in ("output", "log")}
    for path in required:
        path.relative_to(run)
        if not path.is_file():
            raise ValueError(f"Missing saved-run artifact: {path}")
    # Copy the selected photo, its activity, and optional edit inputs. No RAW
    # files are copied, and no command is allowed to alter a development recipe.
    photo = Path(record["output"]).resolve()
    optional = [photo.with_suffix(".strehl-edits.json"), run / "master.tiff",
                run / "confidence.tiff"]
    paths = sorted(required | {path for path in optional if path.is_file()})
    protected = {str(path): digest(path) for path in paths}
    fixture = output / "fixture"
    fixture.mkdir()
    for path in paths:
        relative = path.resolve().relative_to(run)
        destination = fixture / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    # Keep layout and selected run metadata, excluding unrelated project paths.
    isolated_catalog = {
        "layout": catalog.get("layout", {}),
        "runs": [remap_paths(record, run, fixture)],
        "nodes": [], "selected": None, "next_node_id": 1,
    }
    state = output / "state"
    (state / "Strehl").mkdir(parents=True)
    (state / "Strehl/projects.json").write_text(
        json.dumps(isolated_catalog, indent=2), encoding="utf-8"
    )
    return fixture, state, protected


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New, nonexistent directory")
    parser.add_argument("--motions", type=int, default=100)
    parser.add_argument("--size", default="2600x1300")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This audit currently supports native Windows app launches")
    binary, run, catalog, output = (
        item.resolve() for item in (args.binary, args.run, args.catalog, args.output)
    )
    if not binary.is_file() or not run.is_dir() or not catalog.is_file():
        parser.error("Binary, saved run, and catalog must exist")
    if not 1 <= args.motions <= 10000:
        parser.error("--motions must be between 1 and 10000")
    if output == run or output.is_relative_to(run):
        parser.error("--output must be outside the input run")
    if output.exists():
        parser.error("--output must be a fresh directory")
    output.mkdir(parents=True)
    protected = {str(path): digest(path) for path in (catalog, binary)}
    if os.environ.get("LOCALAPPDATA"):
        user_catalog = Path(os.environ["LOCALAPPDATA"]) / "Strehl/projects.json"
        protected[str(user_catalog)] = digest(user_catalog)
    trace = FrameTrace()
    receipt = {
        "binary": str(binary), "binary_sha256": protected[str(binary)],
        "audit_script_sha256": digest(Path(__file__).resolve()),
        "run": str(run), "catalog": str(catalog), "size": args.size,
        "platform": platform.platform(), "processor": platform.processor(),
        "trace": "x=.48+.17*sin(i*.13), y=.5+.14*sin(i*.09), zoom=8",
        "commands": args.motions,
        "meaning": "Paced MCP SetView trace. Complete per-egui-frame CPU observations, "
                   "summing layout passes and attributing previous-frame CPU to its prior ID. "
                   "Includes renderer submission, excludes vsync wait. Not GPU time, FPS, "
                   "pointer latency, or input-to-photon latency.",
        "opening_caveat": "Files are copied before launch; this is not a cold-cache opening test. "
                          "Opening covers only available observations after the MCP connection; "
                          "earlier frames may have left the binary's bounded 256-frame buffer.",
        "passed": False,
    }
    app = mcp = None
    try:
        fixture, state, fixture_inputs = prepare_fixture(run, catalog, output)
        protected.update(fixture_inputs)
        environment = os.environ.copy()
        environment["LOCALAPPDATA"] = str(state)
        environment["XDG_STATE_HOME"] = str(state)
        receipt["launch"] = [str(binary), "--agent", "--open-run", str(fixture),
                             "--size", args.size]
        with (output / "native-app.log").open("w", encoding="utf-8") as app_log, (
            output / "mcp.log"
        ).open("w", encoding="utf-8") as mcp_log:
            started = time.monotonic()
            app = subprocess.Popen(receipt["launch"], cwd=output, env=environment,
                                   stdout=app_log, stderr=app_log,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
            descriptor = None
            deadline = started + 120
            while time.monotonic() < deadline:
                if app.poll() is not None:
                    raise RuntimeError("Native app exited; inspect native-app.log")
                created = list((state / "Strehl/agent-sessions").glob("*/session.json"))
                if len(created) == 1:
                    descriptor = created[0]
                    break
                if len(created) > 1:
                    raise RuntimeError("Unexpected sessions in isolated state directory")
                time.sleep(0.1)
            if descriptor is None:
                raise TimeoutError("Native app did not expose its isolated agent session")
            mcp = subprocess.Popen(
                [str(binary), "--mcp", "--session", str(descriptor)], cwd=output,
                env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=mcp_log, text=True, encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            session = Session(mcp, trace)
            session.rpc("initialize", {
                "protocolVersion": "2025-11-25", "capabilities": {},
                "clientInfo": {"name": "Strehl native performance audit", "version": "1"},
            })
            session.rpc("notifications/initialized", {}, notification=True)
            ready = session.settle(minimum=2.0)
            opening_end = trace.latest
            opening_wall = time.monotonic() - started
            session.drain_after(opening_end)
            receipt["opening"] = {
                **trace.summarize(min(trace.rows), opening_end, require_contiguous=False),
                "wall_seconds": opening_wall, "photo": ready["photo"],
                "development": ready["development"], "display": ready.get("display"),
            }
            print("Opening CPU:", receipt["opening"]["framework_cpu"], flush=True)
            zoom_begin = trace.latest + 1
            session.view([0.38, 0.57], 8)
            session.settle(minimum=1.0)
            zoom_aperture = session.wait_view([0.38, 0.57], 8)
            zoom_end = trace.latest
            session.drain_after(zoom_end)
            receipt["initial_zoom"] = trace.summarize(zoom_begin, zoom_end)
            receipt["initial_zoom"]["painted_uv"] = zoom_aperture
            motion_begin = trace.latest + 1
            motion_started = time.monotonic()
            apertures = []
            for index in range(args.motions):
                center = [
                    0.48 + 0.17 * math.sin(index * 0.13),
                    0.5 + 0.14 * math.sin(index * 0.09),
                ]
                session.view(center, 8)
                apertures.append({"command": index, "center": center,
                                  "painted_uv": session.wait_view(center, 8)})
            finished = session.settle(minimum=0.12)
            if finished["development"] != ready["development"]:
                raise RuntimeError("Development recipe unexpectedly changed during the view trace")
            checked_aperture(finished, apertures[-1]["center"], 8)
            motion_end = trace.latest
            motion_wall = time.monotonic() - motion_started
            session.drain_after(motion_end)
            receipt["motion"] = {
                **trace.summarize(motion_begin, motion_end),
                "commands": args.motions, "wall_seconds": motion_wall,
                "final_display": finished.get("display"),
                "painted_apertures": apertures,
            }
            receipt["passed"] = True
            print("Motion CPU:", receipt["motion"]["framework_cpu"], flush=True)
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        for process in (mcp, app):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=15)
        receipt["input_sha256"] = protected
        receipt["protected_inputs_unchanged"] = all(
            digest(Path(path)) == before for path, before in protected.items()
        )
        if not receipt["protected_inputs_unchanged"]:
            receipt["passed"] = False
        receipt["raw_samples"] = [trace.rows[key] for key in sorted(trace.rows)]
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        if not receipt["protected_inputs_unchanged"]:
            raise RuntimeError("Protected input changed; inspect receipt.json")


if __name__ == "__main__":
    main()
