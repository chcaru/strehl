"""Run one owned command with complete logs and sampled resource provenance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import psutil

p = argparse.ArgumentParser()
p.add_argument("--receipt", required=True, type=Path)
p.add_argument("--cwd", required=True, type=Path)
p.add_argument("--env", action="append", default=[])
p.add_argument("command", nargs=argparse.REMAINDER)
args = p.parse_args()
command = args.command[1:] if args.command[:1] == ["--"] else args.command
if not command:
    p.error("a command is required after --")
args.receipt.mkdir(parents=True, exist_ok=False)
environment = os.environ.copy()
for setting in args.env:
    key, value = setting.split("=", 1)
    environment[key] = value
log_path = args.receipt / "command.log"
started = time.time()
receipt = {
    "command": command,
    "cwd": str(args.cwd.resolve()),
    "started_unix": started,
    "platform": platform.platform(),
    "logical_cpus": psutil.cpu_count(),
    "physical_cpus": psutil.cpu_count(logical=False),
    "physical_memory_bytes": psutil.virtual_memory().total,
    "available_memory_before": psutil.virtual_memory().available,
    "environment": {k: v for k, v in environment.items()
                    if k.startswith(("STREHL_", "RAYON_", "CARGO_"))},
    "sampling_seconds": 1,
    "cpu_accounting": "sampled cumulative owned-process CPU; may miss final interval",
    "state": "running",
}
exe = Path(command[0])
if exe.is_file():
    receipt["executable_sha256"] = hashlib.file_digest(exe.open("rb"), "sha256").hexdigest()
record = args.receipt / "receipt.json"
record.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
max_private = max_rss = max_gpu = 0
cpu_by_pid = {}
with log_path.open("wb") as log, (args.receipt / "resources.jsonl").open("w", encoding="utf-8") as stats:
    process = subprocess.Popen(command, cwd=args.cwd, env=environment, stdout=log, stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    receipt["pid"] = process.pid
    root = psutil.Process(process.pid)
    while process.poll() is None:
        private = rss = 0
        try:
            owned = [root] + root.children(recursive=True)
        except psutil.Error:
            owned = []
        for child in owned:
            try:
                memory = child.memory_info()
                rss += memory.rss
                private += getattr(memory, "private", memory.rss)
                cpu = child.cpu_times()
                cpu_by_pid[child.pid] = cpu.user + cpu.system
            except psutil.Error:
                pass
        max_private = max(max_private, private)
        max_rss = max(max_rss, rss)
        stats.write(json.dumps({"elapsed_seconds": time.time() - started, "rss_bytes": rss,
                               "private_bytes": private, "cpu_seconds": sum(cpu_by_pid.values()),
                               "host_cpu_percent": psutil.cpu_percent(),
                               "available_memory_bytes": psutil.virtual_memory().available}) + "\n")
        stats.flush()
        time.sleep(1)
    exit_code = process.wait()
receipt.update(state="complete" if exit_code == 0 else "failed", exit_code=exit_code,
               elapsed_seconds=time.time() - started, finished_unix=time.time(),
               sampled_peak_private_bytes=max_private, sampled_peak_rss_bytes=max_rss,
               sampled_cpu_seconds=sum(cpu_by_pid.values()),
               available_memory_after=psutil.virtual_memory().available)
record.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, indent=2))
sys.exit(exit_code)
