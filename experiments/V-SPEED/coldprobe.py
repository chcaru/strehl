"""Quantify what a genuinely cold RAW read costs strehl.

Every round of the main runs calls `develop` first, which reads all the .ARW
files and therefore warms the OS file cache before strehl ever sees them. So
even round 0's strehl number is a warm-RAW number, biased in strehl's favour.

This probe uses a subject the main runs never touched, times strehl on it once
(cold), then twice more (warm), and reports the delta. Same perf_counter around
subprocess.run as runner.time_stage, so the number is comparable.

Cross-check on the same quantity: develop's own cold-vs-warm delta on the deep
subject, which is a pure RAW-read-bound stage.
"""

import json
import os
import subprocess
import sys
import time

STREHL = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
OUTROOT = r"C:\dev\strehl-out\V-SPEED"


def run(subject, srcdir, n):
    outdir = os.path.join(OUTROOT, subject, "out")
    logdir = os.path.join(OUTROOT, subject, "logs")
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(logdir, exist_ok=True)
    frames = len([f for f in os.listdir(srcdir) if f.lower().endswith(".arw")])
    print(f"subject {subject}, {frames} frames")
    print(f"{'run':<6} {'state':<6} {'wall_s':>9} {'s/frame':>9}")
    print("-" * 34)
    rows = []
    for i in range(n):
        out = os.path.join(outdir, f"cold{i}-strehl.tif")
        log = os.path.join(logdir, f"cold{i}-strehl.log")
        cmd = [STREHL, "stack", srcdir, "--out", out, "--srgb", "--auto-exposure"]
        t0 = time.perf_counter()
        with open(log, "w", encoding="utf-8", errors="replace") as fh:
            rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode
        dt = time.perf_counter() - t0
        state = "cold" if i == 0 else "warm"
        print(f"{i:<6} {state:<6} {dt:>9.2f} {dt / frames:>9.3f}")
        rows.append({"run": i, "state": state, "wall_s": dt, "rc": rc, "frames": frames})
    with open(os.path.join(OUTROOT, f"coldprobe-{subject}.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    warm = [r["wall_s"] for r in rows if r["state"] == "warm"]
    if warm:
        cold = rows[0]["wall_s"]
        best = min(warm)
        print()
        print(f"cold {cold:.2f} s, warm min {best:.2f} s, cold penalty {cold - best:+.2f} s "
              f"({100 * (cold - best) / best:+.1f}%)")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
