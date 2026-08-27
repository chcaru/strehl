"""Is the fullres speedup LESS WORK or MORE PARALLELISM?

Runs the same A/B at several rayon widths. The plane gather (gather_checked) is
a plain serial loop; the fullres gather is rayon par_chunks_mut. If the win is a
parallelism harvest it must shrink -- and should reverse -- as the pool narrows,
because at one thread the fullres arm does strictly MORE work (mosaic build +
Malvar demosaic of 4x the pixels) for the same number of output samples.
"""
import json, os, re, subprocess, sys, time, statistics
from pathlib import Path

EXE = r"C:\dev\strehl-out\V-GATHER\strehl-pinned.exe"
SRC = Path(r"D:\personal\macro")
OUT = Path(r"C:\dev\strehl-out\V-GATHER")
FOLD = re.compile(r"folded\s+:\s*(\d+) / (\d+) frames in ([\d.]+) s \(([\d.]+) s per frame, (\d+) workers\)")

def one(subject, arm, limit, threads, workers):
    env = dict(os.environ)
    env["STREHL_FULLRES_GATHER"] = arm
    env["STREHL_FIX_CA"] = "off"
    env["RAYON_NUM_THREADS"] = str(threads)
    env["STREHL_PYRAMID_WORKERS"] = str(workers)
    t0 = time.perf_counter()
    r = subprocess.run([EXE, "stack", str(SRC / subject), "--limit", str(limit)],
                       env=env, capture_output=True, text=True)
    wall = time.perf_counter() - t0
    log = r.stdout + r.stderr
    if r.returncode != 0:
        print("RC", r.returncode, log[-1200:]); sys.exit(2)
    f = FOLD.search(log)
    return float(f.group(3)) / int(f.group(2)) * 1000.0, wall, int(f.group(1))

if __name__ == "__main__":
    subj, limit, reps = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    grid = [(int(a), int(b)) for a, b in (s.split(":") for s in sys.argv[4].split(","))]
    rows = []
    for threads, workers in grid:
        for rep in range(reps):
            order = ("1", "0") if rep % 2 == 0 else ("0", "1")
            for arm in order:
                ms, wall, n = one(subj, arm, limit, threads, workers)
                rows.append({"threads": threads, "workers": workers, "arm": arm,
                             "rep": rep, "ms_per_frame": ms, "wall": wall, "folded": n})
                print(f"threads={threads:2d} workers={workers} rep{rep} arm={arm} "
                      f"fold={ms:8.1f} ms/f wall={wall:7.2f}s folded={n}", flush=True)
    (OUT / f"threads-{subj}-{limit}.json").write_text(json.dumps(rows, indent=1))
    print("\n=== SUMMARY: fold ms/frame, median of reps ===")
    print(f"{'threads':>7s} {'workers':>7s} {'g0 (plane)':>12s} {'g1 (fullres)':>13s} {'g1-g0':>10s} {'%':>8s}")
    for threads, workers in grid:
        a0 = statistics.median([r["ms_per_frame"] for r in rows
                                if r["threads"] == threads and r["arm"] == "0"])
        a1 = statistics.median([r["ms_per_frame"] for r in rows
                                if r["threads"] == threads and r["arm"] == "1"])
        print(f"{threads:7d} {workers:7d} {a0:12.1f} {a1:13.1f} {a1-a0:+10.1f} {100*(a1-a0)/a0:+8.2f}")
