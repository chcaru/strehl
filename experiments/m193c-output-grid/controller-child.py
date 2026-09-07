"""Literal process-boundary fixtures. Never decodes or writes image data."""
import os
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def marker(path, value):
    raw = (json.dumps(value, sort_keys=True) + "\n").encode()
    assert len(raw) <= 1024 and not path.exists()
    pending = path.with_suffix(path.suffix + ".pending")
    with pending.open("xb") as stream:
        assert stream.write(raw) == len(raw)
        stream.flush()
        os.fsync(stream.fileno())
    pending.rename(path)


mode = sys.argv[1]
if mode == "valid":
    print("M193C_VALID_CHILD", flush=True)
elif mode == "nonzero":
    print("M193C_EXIT_SEVEN", flush=True)
    raise SystemExit(7)
elif mode in ("exact-log", "overflow-log"):
    count = 65536 if mode == "exact-log" else 65537
    sys.stdout.buffer.write(b"x" * count)
    sys.stdout.buffer.flush()
elif mode == "timeout":
    print("M193C_SLEEP_STARTED", flush=True)
    print("M193C_SLEEP_PID=" + str(os.getpid()), flush=True)
    time.sleep(30)
elif mode == "nested-timeout":
    print("M193C_PARENT_PID=" + str(os.getpid()), flush=True)
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "timeout"],
                             stdin=subprocess.DEVNULL, stdout=sys.stdout.buffer, stderr=subprocess.STDOUT,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    print("M193C_NESTED_PID=" + str(child.pid), flush=True)
    child.wait()
elif mode in ("memory", "memory-allowed"):
    try:
        allocation = bytearray(128 << 20)
        print("M193C_MEMORY_ALLOWED=" + str(len(allocation)), flush=True)
        raise SystemExit(0 if mode == "memory-allowed" else 9)
    except MemoryError:
        print("M193C_MEMORY_REFUSED", flush=True)
        raise SystemExit(7)
elif mode == "changed-input":
    path = Path(sys.argv[2])
    assert path.is_absolute() and path.is_file()
    path.write_bytes(b"changed-private-input")
    print("M193C_CHANGED_PRIVATE_INPUT", flush=True)
elif mode in ("drain-finish", "drain-persist", "drain-restored", "drain-descendant"):
    directory = Path(sys.argv[2]).resolve()
    assert directory.is_relative_to(Path(__file__).resolve().parent) and directory.is_dir()
    if mode == "drain-descendant":
        fixture = sys.argv[3]
        assert fixture in ("drain-finish", "drain-persist", "drain-restored")
        delay = 30 if fixture == "drain-persist" else 2
        started = time.monotonic_ns()
        identity = dict(mode=fixture, parent_pid=os.getppid(), child_pid=os.getpid(), started_monotonic_ns=started)
        marker(directory / "startup.json", dict(schema="m193c-controller-drain-start-v1", **identity))
        time.sleep(delay)
        marker(directory / "completion.json", dict(schema="m193c-controller-drain-complete-v1", **identity,
               delay_seconds=delay, completed_monotonic_ns=time.monotonic_ns()))
    else:
        child = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "drain-descendant",
                                  str(directory), mode], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 3
        startup = directory / "startup.json"
        while not startup.exists():
            assert child.poll() is None, "descendant exited before startup marker"
            assert time.monotonic() <= deadline, "descendant startup marker deadline"
            time.sleep(.01)
        with startup.open("rb") as stream:
            raw = stream.read(1025)
        assert len(raw) <= 1024
        observed = json.loads(raw)
        assert observed["schema"] == "m193c-controller-drain-start-v1" and observed["mode"] == mode
        assert observed["child_pid"] == child.pid and observed["parent_pid"] == os.getpid()
        assert child.poll() is None, "actual descendant must remain live at parent exit"
        print("M193C_DRAIN_PARENT=" + json.dumps(dict(parent_pid=os.getpid(), requested_child_pid=child.pid,
              started_child_pid=observed["child_pid"], child_live=True,
              startup_sha256=hashlib.sha256(raw).hexdigest()), sort_keys=True), flush=True)
        # Intentionally no wait: DEVNULL descendant cannot retain the direct child's output pipe.
else:
    raise ValueError("unregistered controller child mode")
