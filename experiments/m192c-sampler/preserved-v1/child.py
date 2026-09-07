"""Bounded synthetic workload with independent allocation and scheduling receipts."""
import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetCurrentProcessorNumber.restype = wt.DWORD
k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
k32.VirtualAlloc.restype = ctypes.c_void_p
k32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD]
k32.VirtualFree.restype = wt.BOOL


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["null", "pulse", "spawn", "short", "fixed", "fixed-slow"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    def event(name, **values):
        rows.append({"event": name, "qpc_ns": time.perf_counter_ns(), "cpu_s": time.process_time(),
                     "cpu_number": int(k32.GetCurrentProcessorNumber()), "pid": os.getpid(), **values})
    event("start", parent_pid=os.getppid(), mode=args.mode)
    output_class = args.mode
    if args.mode == "null":
        time.sleep(.55)
    elif args.mode in ("pulse", "short"):
        if args.mode == "pulse":
            time.sleep(.15)
        size = (64 if args.mode == "pulse" else 24) * 1024**2
        event("allocate-begin", requested_bytes=size)
        address = k32.VirtualAlloc(None, size, 0x3000, 0x04)
        if not address:
            raise ctypes.WinError(ctypes.get_last_error())
        ctypes.memset(address, 0x59, size)
        event("allocated-touched", committed_bytes=size)
        time.sleep(.18 if args.mode == "pulse" else .08)
        event("release-begin")
        if not k32.VirtualFree(address, 0, 0x8000):
            raise ctypes.WinError(ctypes.get_last_error())
        event("released", released_bytes=size)
        time.sleep(.18 if args.mode == "pulse" else .015)
    elif args.mode == "spawn":
        event("spawn-begin")
        child = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()),
            "--mode", "short", "--output", str(args.output.with_suffix(".child.bin")),
            "--receipt", str(args.receipt.with_suffix(".child.json"))], creationflags=subprocess.CREATE_NO_WINDOW)
        event("spawned", child_pid=child.pid)
        code = child.wait()
        event("child-exited", child_pid=child.pid, returncode=code)
        assert code == 0
        time.sleep(.20)
    else:
        output_class = "fixed"
        block = bytes(range(256))*4096
        event("fixed-work-begin", rounds=512, block_bytes=len(block))
        for _ in range(512):
            digest = hashlib.sha256(block).digest()
        event("fixed-work-end", digest=digest.hex())
        if args.mode == "fixed-slow":
            event("slow-begin")
            time.sleep(.25)
            event("slow-end")
    args.output.write_bytes(b"M192c deterministic synthetic output\n" + output_class.encode() + b"\n" + bytes(range(256))*16)
    event("end", output_bytes=args.output.stat().st_size)
    args.receipt.write_text(json.dumps(rows, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
