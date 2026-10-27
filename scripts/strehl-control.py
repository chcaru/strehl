#!/usr/bin/env python3
"""Launch and control Strehl through its existing one-shot local mailbox client."""

import argparse
import json
import math
import os
import signal
from pathlib import Path
import subprocess
import sys
import time

MAX_PUBLICATION_BYTES = 4096
MAX_REPLY_BYTES = 8 * 1024 * 1024
SCREENSHOT_TIMEOUT_SECONDS = 70


class ControlError(Exception):
    pass


def emit(value):
    # ASCII escaping also keeps this usable in legacy Windows console encodings.
    print(json.dumps(value, ensure_ascii=True, separators=(",", ":")), flush=True)


def publication(path):
    with path.open("rb") as stream:
        content = stream.read(MAX_PUBLICATION_BYTES + 1)
    if len(content) > MAX_PUBLICATION_BYTES:
        raise ControlError("Session publication exceeds 4096 bytes")
    value = json.loads(content)
    if not isinstance(value, dict) or type(value.get("schema")) is not int or value["schema"] != 1:
        raise ControlError("Expected a schema-1 Strehl session publication")
    pid = value.get("pid")
    session = value.get("session")
    if type(pid) is not int or pid <= 0 or not isinstance(session, str):
        raise ControlError("Session publication lacks a valid PID or session path")
    descriptor = Path(session)
    if not descriptor.is_absolute() or descriptor.name != "session.json":
        raise ControlError("Publication must name an absolute session.json path")
    return value


def subprocess_options():
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def invoke(args, session, *, request_path=None, request_bytes=None):
    command = [str(args.exe), "--control", "--session", session]
    options = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE,
               "timeout": args.timeout, **subprocess_options()}
    if request_bytes is not None:
        command += ["--request", "-"]
        options["input"] = request_bytes
    elif request_path is not None:
        command += ["--request", request_path]
        options["stdin"] = sys.stdin.buffer if request_path == "-" else subprocess.DEVNULL
    else:
        options["stdin"] = subprocess.DEVNULL
    try:
        result = subprocess.run(command, **options)
    except subprocess.TimeoutExpired as error:
        raise ControlError(
            "Control client timed out; the command may have been accepted. "
            "Read a snapshot before reconsidering a mutation; it was not retried."
        ) from error
    if not result.stdout:
        detail = result.stderr.decode("utf-8", errors="replace").strip()[:2048]
        error = detail or f"Control client returned no reply (exit {result.returncode})"
        return {"data": {}, "error": error}, result.returncode if result.returncode in (1, 2) else 1
    if len(result.stdout) > MAX_REPLY_BYTES + 1:
        raise ControlError("Control reply exceeds the fixed 8 MiB limit")
    try:
        reply = json.loads(result.stdout)
    except (ValueError, UnicodeError) as error:
        raise ControlError("Control client did not return exactly one JSON AgentReply") from error
    if not isinstance(reply, dict) or "data" not in reply:
        raise ControlError("Control client did not return an AgentReply object")
    if result.returncode not in (0, 1, 2):
        raise ControlError(f"Control client failed with exit {result.returncode}")
    return reply, result.returncode or int(reply.get("error") is not None)


def launch(args):
    pointer = args.session_file
    if pointer.exists():
        raise ControlError("Session publication already exists; select a fresh --session-file path")
    if not pointer.parent.is_dir():
        raise ControlError("Create the --session-file parent directory before launching")
    log_path = pointer.with_name(pointer.name + ".log")
    command = [str(args.exe), "--agent" if args.gui else "--headless",
               "--agent-session-out", str(pointer)]
    for option, value in (("--source", args.source), ("--output-dir", args.output_dir),
                          ("--catalog", args.catalog or pointer.with_suffix(".projects.json"))):
        if value is not None:
            command += [option, str(value.resolve())]
    for grant in args.grant:
        command += ["--agent-grant", str(grant.resolve())]
    options = subprocess_options()
    if os.name != "nt":
        options["start_new_session"] = True
    with log_path.open("ab") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, **options)
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        status = process.poll()
        if status is not None:
            raise ControlError(f"Strehl exited with status {status}; inspect {log_path}")
        try:
            info = publication(pointer)
        except (FileNotFoundError, ValueError, UnicodeError):
            # Publication creation and its bounded JSON write are separate steps.
            time.sleep(0.05)
            continue
        if info["pid"] != process.pid:
            raise ControlError(
                f"Publication belongs to a different process; launched PID {process.pid} "
                f"was left running. Inspect {log_path}"
            )
        emit({"data": {"state": "session_published", "pid": process.pid,
                       "session_file": str(pointer), "session": info["session"],
                       "build": info.get("build"), "headless": not args.gui,
                       "log_file": str(log_path)}})
        if args.wait:
            status = process.wait()
            emit({"data": {"state": "process_exited", "pid": process.pid,
                           "exit_code": status}})
            return 0 if status == 0 else 1
        return 0
    raise ControlError(
        f"Publication timed out; launched PID {process.pid} was left running. "
        f"Inspect {log_path} and {pointer} before launching again"
    )




def terminate_owned_tree(process, log):
    """Escalate only the still-owned Popen child/group, then reap its parent."""
    errors = []
    tree_command_succeeded = False
    method = "taskkill /T /F" if os.name == "nt" else "killpg SIGKILL"
    try:
        if os.name == "nt":
            taskkill = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "taskkill.exe")
            result = subprocess.run(
                [taskkill, "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                timeout=10, **subprocess_options())
            if result.returncode != 0:
                raise ControlError(f"taskkill exited with {result.returncode}")
        else:
            # screenshot() starts this exact child in a new session, so its PID
            # also identifies the process group owned by this helper.
            os.killpg(process.pid, signal.SIGKILL)
        tree_command_succeeded = True
    except (OSError, subprocess.TimeoutExpired, ControlError) as error:
        errors.append(f"Process-tree cleanup failed: {error}")
        try:
            if process.poll() is None:
                process.kill()
        except OSError as fallback:
            errors.append(f"Fallback parent kill failed: {fallback}")
    parent_reaped = False
    try:
        process.communicate(timeout=10)
        parent_reaped = True
    except (OSError, subprocess.TimeoutExpired) as error:
        errors.append(f"Owned parent was not reaped: {error}")
    cleanup = {"method": method, "pid": process.pid,
               "tree_cleanup": "succeeded" if tree_command_succeeded and parent_reaped else "unconfirmed",
               "parent_reaped": parent_reaped, "parent_exit_code": process.returncode,
               "errors": errors}
    log.write((json.dumps({"event": "offscreen_cleanup", **cleanup}) + "\n").encode("utf-8"))
    log.flush()
    return cleanup


def screenshot(args):
    png = args.png.resolve()
    if png.exists():
        raise ControlError("Screenshot already exists; choose a fresh --png path")
    if not png.parent.is_dir():
        raise ControlError("Create the --png parent directory before rendering")
    source = args.source.resolve(strict=True)
    if not source.is_dir():
        raise ControlError("--source must name a directory")
    log_path = png.with_name(png.name + ".log")
    catalog = (args.catalog or png.with_suffix(".projects.json")).resolve()
    command = [str(args.exe), "--offscreen-screenshot", str(png),
               "--source", str(source), "--catalog", str(catalog)]
    if args.metadata:
        command.append("--metadata")
    if args.output_dir is not None:
        command += ["--output-dir", str(args.output_dir.resolve())]
    if args.size is not None:
        command += ["--size", args.size]
    details = {"png": str(png), "log_file": str(log_path)}
    with log_path.open("ab") as log:
        log.write((json.dumps({"event": "offscreen_launch", "command": command}) + "\n").encode("utf-8"))
        log.flush()
        options = subprocess_options()
        if os.name != "nt":
            options["start_new_session"] = True
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, **options)
        details["pid"] = process.pid
        try:
            process.communicate(timeout=SCREENSHOT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            log.write(b'{"event":"offscreen_timeout","timeout_seconds":70}\n')
            cleanup = terminate_owned_tree(process, log)
            suffix = ("Owned process-tree termination succeeded and the parent was reaped."
                      if cleanup["tree_cleanup"] == "succeeded"
                      else "Descendant cleanup is unconfirmed; inspect the cleanup log before continuing.")
            emit({"data": {**details, "state": "timed_out", "exit_code": process.returncode,
                            "cleanup": cleanup},
                  "error": f"Offscreen process exceeded 70 seconds. {suffix} It was not retried."})
            return 1
        status = process.returncode
        log.write((json.dumps({"event": "offscreen_exit", "exit_code": status}) + "\n").encode("utf-8"))
    details["exit_code"] = status
    if status != 0:
        emit({"data": {**details, "state": "failed"},
              "error": f"Offscreen rendering failed with exit {status}; inspect the log"})
        return status if status in (1, 2) else 1
    try:
        with png.open("rb") as image:
            header = image.read(24)
            image.seek(-12, os.SEEK_END)
            ending = image.read(12)
        if (len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n"
                or header[8:16] != b"\x00\x00\x00\x0dIHDR"
                or ending != b"\x00\x00\x00\x00IEND\xae\x42\x60\x82"):
            raise ControlError("Output is missing a PNG header or complete IEND chunk")
        dimensions = [int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")]
        if min(dimensions) <= 0:
            raise ControlError("Output PNG has invalid dimensions")
    except (OSError, ControlError) as error:
        emit({"data": {**details, "state": "invalid_output"}, "error": str(error)})
        return 1
    emit({"data": {**details, "state": "screenshot_saved", "size": dimensions,
                   "byte_length": png.stat().st_size}})
    return 0


def positive_timeout(value):
    seconds = float(value)
    if not math.isfinite(seconds) or not 0 < seconds <= 300:
        raise argparse.ArgumentTypeError("timeout must be greater than 0 and at most 300 seconds")
    return seconds


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--exe", required=True, type=Path, help="packaged Strehl executable")
    result.add_argument("--session-file", type=Path,
                        help="required except for screenshot: public --agent-session-out pointer, not session.json")
    result.add_argument("--timeout", type=positive_timeout, default=30,
                        help="bounded launch/control wait in seconds (default: 30)")
    commands = result.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("screenshot", help="render the real workspace offscreen and wait up to 70 seconds")
    capture.add_argument("--source", required=True, type=Path, help="source directory to import")
    capture.add_argument("--png", required=True, type=Path, help="fresh PNG output path")
    capture.add_argument("--metadata", action="store_true", help="open the native camera metadata panel")
    capture.add_argument("--output-dir", type=Path, help="generated results and metadata reports")
    capture.add_argument("--catalog", type=Path, help="isolated catalog (default: PNG path with .projects.json)")
    capture.add_argument("--size", metavar="WxH", help="canvas dimensions, for example 1440x940")
    start = commands.add_parser("launch", help="start headless and wait for session publication")
    start.add_argument("--source", type=Path, help="source directory to import")
    start.add_argument("--grant", action="append", type=Path, default=[],
                       help="explicitly share a directory; repeat for separate roots")
    start.add_argument("--output-dir", type=Path, help="generated results and metadata reports")
    start.add_argument("--catalog", type=Path, help="separate headless projects catalog")
    start.add_argument("--gui", action="store_true", help="explicitly open a native window instead")
    start.add_argument("--wait", action="store_true",
                       help="flush publication JSON, then stay attached until the owned process exits")
    commands.add_parser("snapshot", aliases=["status"], help="read one complete workspace snapshot")
    call = commands.add_parser("call", help="send exactly one supplied AgentRequest")
    call.add_argument("--request", required=True, help="JSON request file, or '-' for stdin")
    commands.add_parser("shutdown", aliases=["stop"],
                        help="snapshot once, then request idle headless shutdown once")
    return result


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if args.command != "screenshot" and args.session_file is None:
        cli.error("--session-file is required for this command")
    try:
        args.exe = args.exe.resolve(strict=True)
        if not args.exe.is_file():
            raise ControlError("--exe must name a file")
        if args.command == "screenshot":
            return screenshot(args)
        args.session_file = args.session_file.resolve()
        if args.command == "launch":
            return launch(args)
        info = publication(args.session_file)
        if args.command == "call":
            reply, status = invoke(args, info["session"], request_path=args.request)
        else:
            reply, status = invoke(args, info["session"])
            if args.command in ("shutdown", "stop") and status == 0:
                data = reply.get("data")
                revision = data.get("revision") if isinstance(data, dict) else None
                if type(revision) is not int or revision < 0:
                    raise ControlError("Snapshot lacks a valid workspace revision; shutdown was not sent")
                request = {"expected_revision": revision, "command": {"operation": "shutdown"}}
                reply, status = invoke(args, info["session"], request_bytes=json.dumps(request).encode("utf-8"))
        emit(reply)
        return status
    except (ControlError, OSError, ValueError, UnicodeError) as error:
        emit({"data": {}, "error": str(error)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
