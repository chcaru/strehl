"""How parallel is each arm, measured rather than assumed.

Brief item 7: "Do not tune our arm and not theirs. If you give strehl a thread
count, give enfuse its equivalent. State the parallelism settings for all
arms." No arm was given a thread count -- every one ran at its own default --
so the honest way to state the settings is to measure what each default
actually did.

METHOD. Run each stage once under subprocess.Popen, then read the child's
kernel+user CPU time out of GetProcessTimes() before the handle closes. The
ratio cpu_s / wall_s is the mean number of cores the stage kept busy. It needs
no new dependency and it does not care what other agents are doing, because it
counts only this process's own CPU.

LIMIT, stated: GetProcessTimes covers the process, not its descendants. Every
stage here is a single process except `develop`, which forks a worker pool --
so develop's own ratio reads ~1 and its real parallelism is the WORKERS
constant in runner.py plus the cpu_s_sum its JSON already reports.

Usage: python parallelism.py <subject> <src>
"""

import ctypes
import ctypes.wintypes as wt
import glob
import json
import os
import subprocess
import sys
import time

import runner


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wt.DWORD), ("dwHighDateTime", wt.DWORD)]


def _ft(ft):
    return ((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 1e7  # 100 ns units


def run_with_cpu(cmd, log, cwd=None):
    creation, exitt, kernel, user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
    os.makedirs(os.path.dirname(log), exist_ok=True)
    t0 = time.perf_counter()
    with open(log, "wb") as lf:
        p = subprocess.Popen(cmd, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT)
        rc = p.wait()
        ok = ctypes.windll.kernel32.GetProcessTimes(
            int(p._handle),
            ctypes.byref(creation),
            ctypes.byref(exitt),
            ctypes.byref(kernel),
            ctypes.byref(user),
        )
    wall = time.perf_counter() - t0
    if not ok:
        raise SystemExit("GetProcessTimes failed; refusing to report parallelism")
    cpu = _ft(kernel) + _ft(user)
    return {"wall_s": wall, "cpu_s": cpu, "cores": cpu / wall, "rc": rc}


def main():
    subject, src = sys.argv[1], sys.argv[2]
    runner.check_binaries()
    base = os.path.join(runner.ROOT, subject)
    tifdir = os.path.join(base, "tif-srgb")
    aligndir = os.path.join(base, "aligned")
    outdir = os.path.join(base, "out")
    logdir = os.path.join(base, "logs")
    tifs = sorted(glob.glob(os.path.join(tifdir, "*.tif")))
    als = sorted(glob.glob(os.path.join(aligndir, "al_*.tif")))
    nframes = len([n for n in os.listdir(src) if n.lower().endswith(".arw")])

    stages = [
        (
            "strehl",
            [runner.STREHL, "stack", src, "--out", os.path.join(outdir, "par-strehl.tif"),
             "--srgb", "--auto-exposure"],
            None,
        ),
        (
            "enfuse",
            [runner.ENFUSE] + runner.ENFUSE_FLAGS
            + [f"--output={os.path.join(outdir, 'par-enfuse.tif')}"] + als,
            None,
        ),
        (
            "focus-stack",
            [runner.FS, f"--output={os.path.join(outdir, 'par-fs.tif')}"] + tifs,
            None,
        ),
        (
            "align",
            [runner.AIS] + runner.AIS_FLAGS + ["-a", "par_"] + tifs,
            aligndir,
        ),
    ]

    print(f"subject {subject}, {nframes} frames, {os.cpu_count()} logical processors\n")
    print(f"{'stage':<14}{'wall_s':>9}{'cpu_s':>10}{'mean cores busy':>17}")
    print("-" * 50)
    out = []
    for name, cmd, cwd in stages:
        r = run_with_cpu(cmd, os.path.join(logdir, f"par-{name}.log"), cwd=cwd)
        r["stage"] = name
        r["subject"] = subject
        r["frames"] = nframes
        out.append(r)
        print(f"{name:<14}{r['wall_s']:>9.2f}{r['cpu_s']:>10.2f}{r['cores']:>17.2f}")
    for f in glob.glob(os.path.join(aligndir, "par_*.tif")):
        os.remove(f)
    with open(os.path.join(runner.ROOT, "parallelism.jsonl"), "a", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
