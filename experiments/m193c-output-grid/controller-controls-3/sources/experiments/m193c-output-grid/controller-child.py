"""Literal process-boundary fixtures. Never decodes or writes image data."""
import os
from pathlib import Path
import subprocess
import sys
import time

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
else:
    raise ValueError("unregistered controller child mode")
