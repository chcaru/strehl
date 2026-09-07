"""Verifier-owned allocation stimulus, independent of the author's workload."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

folder = Path(sys.argv[1])
if len(sys.argv) == 2:
    process = subprocess.Popen([sys.executable, "-B", __file__, str(folder), "allocate"])
    assert process.wait() == 0
    time.sleep(.12)
    (folder / "output.bin").write_bytes(bytes(range(256)) * 128)
else:
    events = []
    def event(name):
        events.append({"name": name, "time_ns": time.perf_counter_ns(), "pid": os.getpid()})
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]
    api.VirtualAlloc.restype = ctypes.c_void_p
    api.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32]
    api.VirtualFree.restype = ctypes.c_int
    event("start")
    time.sleep(.1)
    pointer = api.VirtualAlloc(None, 36 * 2**20, 0x3000, 4)
    assert pointer
    ctypes.memset(pointer, 0xA5, 36 * 2**20)
    event("allocated")
    time.sleep(.06)
    event("release")
    assert api.VirtualFree(pointer, 0, 0x8000)
    event("released")
    time.sleep(.08)
    event("end")
    (folder / "events.json").write_text(json.dumps(events), encoding="utf-8")
