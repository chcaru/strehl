"""Time `strehl stack` end to end, on the DEFAULT (pyramid) path.

Why this exists: the README's 51.6 s headline was measured on `--merge
estimator`, which is no longer the default. `experiments/ORCH-drift-check/
retime.py` is the harness that produced 51.6 s (SYNTHESIS fact 1354, at
`925d03d`); this one keeps its methodology -- warm the page cache once, then
report the MINIMUM of N runs because a speed claim is a capability claim --
and adds four things that number needs and did not have:

  * PROVENANCE. The exe's SHA-256 and the commit it was built from are written
    into every record, because at least six `strehl.exe` binaries exist on this
    machine and a timing whose binary cannot be named is worthless (rule 47).
  * THE STAGE BREAKDOWN the binary already prints, parsed rather than
    re-instrumented. `crates/` is read-only for this agent.
  * MACHINE LOAD, sampled over each run's own interval via GetSystemTimes, and
    the child's own CPU-seconds via GetProcessTimes. This box runs a dozen
    agents; a wall-clock number taken on it is a BOUND, not a value (M118 Y10),
    and the only way a later reader can tell how loose that bound is, is if the
    load is recorded beside the time.
  * PEAK WORKING SET, read once from the kernel's own counter after exit, so it
    costs nothing and cannot perturb the timing. The architecture claims memory
    is O(workers) and not O(frames); at 299 frames that is checkable.

Every run's validity is checked by the caller, not here: this file times and
records, it does not judge.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import re
import subprocess
import time

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wt.DWORD), ("dwHighDateTime", wt.DWORD)]

    def value(self) -> int:
        return (self.dwHighDateTime << 32) | self.dwLowDateTime


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def system_times() -> tuple[int, int, int]:
    idle, krnl, user = FILETIME(), FILETIME(), FILETIME()
    if not kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(krnl), ctypes.byref(user)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return idle.value(), krnl.value(), user.value()


def process_cpu_seconds(handle: int) -> float:
    """Kernel + user CPU seconds burned by one process. 0.0 if unreadable."""
    c, e, k, u = FILETIME(), FILETIME(), FILETIME(), FILETIME()
    ok = kernel32.GetProcessTimes(
        wt.HANDLE(handle),
        ctypes.byref(c),
        ctypes.byref(e),
        ctypes.byref(k),
        ctypes.byref(u),
    )
    if not ok:
        return 0.0
    return (k.value() + u.value()) / 1e7


def peak_working_set_bytes(handle: int) -> int:
    """The kernel's own high-water mark. Valid on an exited process's handle."""
    pmc = PROCESS_MEMORY_COUNTERS()
    pmc.cb = ctypes.sizeof(pmc)
    fn = getattr(kernel32, "K32GetProcessMemoryInfo", None)
    if fn is None:
        return 0
    if not fn(wt.HANDLE(handle), ctypes.byref(pmc), pmc.cb):
        return 0
    return int(pmc.PeakWorkingSetSize)


STAGES = {
    # label            regex over the binary's own stderr
    "first_decode_s": re.compile(r"first decode ([\d.]+) s"),
    "align_s": re.compile(r"alignment\s+: ON \(([^)]*)\).*?([\d.]+) s"),
    "fold_s": re.compile(r"folded\s+: (\d+) / (\d+) frames in ([\d.]+) s"),
    "write_s": re.compile(r"collapse\+write\s+: ([\d.]+) s"),
    "total_s": re.compile(r"^total\s+: ([\d.]+) s", re.M),
    "workers": re.compile(r"memory plan\s+: (\d+) workers x ([\d.]+) MB"),
    "geometry": re.compile(r"\((\d+) x (\d+), 16-bit"),
    "backend": re.compile(r"merge backend\s+: (\S+)"),
    "gate": re.compile(r"noise gate\s+: ([\d.]+) x"),
    "exposure": re.compile(r"exposure\s+: ([+-][\d.]+) stops"),
}


def parse_stages(err: str) -> dict:
    out: dict[str, object] = {}
    m = STAGES["first_decode_s"].search(err)
    if m:
        out["first_decode_s"] = float(m.group(1))
    m = STAGES["align_s"].search(err)
    if m:
        out["align_how"] = m.group(1)
        out["align_s"] = float(m.group(2))
    elif "alignment       : OFF" in err:
        out["align_how"] = "off"
        out["align_s"] = 0.0
    m = STAGES["fold_s"].search(err)
    if m:
        out["folded"] = int(m.group(1))
        out["frames"] = int(m.group(2))
        out["fold_s"] = float(m.group(3))
    m = STAGES["write_s"].search(err)
    if m:
        out["write_s"] = float(m.group(1))
    m = STAGES["total_s"].search(err)
    if m:
        out["total_s"] = float(m.group(1))
    m = STAGES["workers"].search(err)
    if m:
        out["workers"] = int(m.group(1))
        out["worker_mb"] = float(m.group(2))
    m = STAGES["geometry"].search(err)
    if m:
        out["out_w"], out["out_h"] = int(m.group(1)), int(m.group(2))
    for key in ("backend", "gate", "exposure"):
        m = STAGES[key].search(err)
        if m:
            out[key] = m.group(1)
    return out


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest().upper()


def raw_bytes(dirpath: str, limit: int | None) -> tuple[int, int]:
    names = sorted(f for f in os.listdir(dirpath) if f.lower().endswith(".arw"))
    if limit:
        names = names[:limit]
    return len(names), sum(os.path.getsize(os.path.join(dirpath, n)) for n in names)


def one_run(exe: str, argv: list[str], dst: str) -> dict:
    if dst and os.path.exists(dst):
        os.remove(dst)
    i0, k0, u0 = system_times()
    t0 = time.perf_counter()
    p = subprocess.Popen(
        [exe] + argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    out, err = p.communicate()
    wall = time.perf_counter() - t0
    i1, k1, u1 = system_times()
    handle = int(p._handle)  # noqa: SLF001  -- Windows-only, valid after exit
    rec = {
        "wall_s": wall,
        "rc": p.returncode,
        "proc_cpu_s": process_cpu_seconds(handle),
        "peak_ws_bytes": peak_working_set_bytes(handle),
    }
    busy = (k1 - k0) + (u1 - u0) - (i1 - i0)
    span = (k1 - k0) + (u1 - u0)
    rec["machine_busy_frac"] = (busy / span) if span else 0.0
    rec.update(parse_stages(err))
    rec["stderr_tail"] = err[-600:] if p.returncode != 0 else ""
    rec["_stderr"] = err
    rec["_stdout"] = out
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--label", required=True)
    ap.add_argument("--commit", default=os.environ.get("BS_COMMIT", "?"))
    ap.add_argument("--log", default=r"C:\dev\strehl-out\BUILD-SPEED\timings.jsonl")
    ap.add_argument("--keep", action="store_true", help="keep the last output file")
    ap.add_argument("--flag", action="append", default=[], help="extra CLI flag")
    args = ap.parse_args()

    exe_hash = sha256(args.exe)
    n_frames, n_bytes = raw_bytes(args.dir, args.limit)
    argv = ["stack", args.dir, "--out", args.out] + args.flag
    if args.limit:
        argv += ["--limit", str(args.limit)]

    env_record = {
        v: os.environ.get(v)
        for v in (
            "STREHL_ALIGN",
            "STREHL_WARPMAP",
            "STREHL_CACHE_DIR",
            "STREHL_MERGE",
            "STREHL_PHOTOMETRIC",
            "STREHL_FIX_CA",
            "STREHL_PYRAMID_WORKERS",
            "RAYON_NUM_THREADS",
        )
    }

    print(f"label       : {args.label}")
    print(f"exe         : {args.exe}")
    print(f"exe sha256  : {exe_hash}")
    print(f"commit      : {args.commit}")
    print(f"command     : strehl {' '.join(argv)}")
    print(f"env         : {json.dumps(env_record)}")
    print(f"frames      : {n_frames}   raw bytes: {n_bytes:,}")
    print()

    runs = []
    for i in range(args.reps):
        rec = one_run(args.exe, argv, args.out)
        rec.update(
            label=args.label,
            rep=i,
            exe=args.exe,
            exe_sha256=exe_hash,
            commit=args.commit,
            argv=argv,
            env=env_record,
            n_frames=n_frames,
            raw_bytes=n_bytes,
            when=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        if rec["rc"] == 0 and os.path.exists(args.out):
            rec["out_bytes"] = os.path.getsize(args.out)
            rec["out_sha256"] = sha256(args.out)
        stderr = rec.pop("_stderr")
        rec.pop("_stdout")
        print(
            "  rep %d  rc=%d  wall %7.2f s  total %7s  decode0 %5s  align %6s (%s)  "
            "fold %7s  write %5s  busy %4.0f%%  cpu %7.1f s  peakWS %6.2f GB"
            % (
                i,
                rec["rc"],
                rec["wall_s"],
                rec.get("total_s", "-"),
                rec.get("first_decode_s", "-"),
                rec.get("align_s", "-"),
                rec.get("align_how", "-"),
                rec.get("fold_s", "-"),
                rec.get("write_s", "-"),
                100 * rec["machine_busy_frac"],
                rec["proc_cpu_s"],
                rec["peak_ws_bytes"] / (1 << 30),
            ),
            flush=True,
        )
        if rec["rc"] != 0:
            print("    FAILED. stderr tail:\n" + rec["stderr_tail"])
        with open(args.log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        if i == args.reps - 1:
            side = args.out + ".stderr.txt"
            with open(side, "w", encoding="utf-8") as fh:
                fh.write(stderr)
            print(f"    last run's stderr -> {side}")
        runs.append(rec)

    ok = [r for r in runs if r["rc"] == 0]
    if not ok:
        print("\nNO SUCCESSFUL RUN")
        return
    walls = sorted(r["wall_s"] for r in ok)
    mb = n_bytes / 1e6
    print()
    print(
        "BEST %.2f s   MEDIAN %.2f s   WORST %.2f s   (%d/%d ok)"
        % (walls[0], walls[len(walls) // 2], walls[-1], len(ok), len(runs))
    )
    print(
        "throughput on best: %.1f MB/s over %.1f MB   %.4f s/frame   peak WS %.2f GB"
        % (
            mb / walls[0],
            mb,
            walls[0] / n_frames,
            max(r["peak_ws_bytes"] for r in ok) / (1 << 30),
        )
    )


if __name__ == "__main__":
    main()
