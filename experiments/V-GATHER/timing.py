"""V-GATHER timing: interleaved A/B on ONE pinned binary, warm warpmap cache.

Reports the binary's own `folded` stage (decode + warp + pyramid fold), which is
the only stage warp_frame_in_place can reach, plus wall clock. No --out: the
write is identical on both arms and only adds disk contention.
"""
import json, os, re, subprocess, sys, time, statistics
from pathlib import Path

EXE = r"C:\dev\strehl-out\V-GATHER\strehl-pinned.exe"
SRC = Path(r"D:\personal\macro")
OUT = Path(r"C:\dev\strehl-out\V-GATHER")

FOLD = re.compile(r"folded\s+:\s*(\d+) / (\d+) frames in ([\d.]+) s \(([\d.]+) s per frame, (\d+) workers\)")
ALIGN = re.compile(r"alignment\s+: ON \((\w[\w-]*)\).*?, (\d+) placed / (\d+) refused, ([\d.]+) s")
TOTAL = re.compile(r"^total\s+:\s*([\d.]+) s", re.M)
MEM = re.compile(r"memory plan\s+: (\d+) workers x ([\d.]+) MB")

def one(subject, arm, limit):
    env = dict(os.environ)
    env["STREHL_FULLRES_GATHER"] = arm
    env["STREHL_FIX_CA"] = "off"
    cmd = [EXE, "stack", str(SRC / subject), "--limit", str(limit)]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    wall = time.perf_counter() - t0
    log = r.stdout + r.stderr
    f = FOLD.search(log); a = ALIGN.search(log); t = TOTAL.search(log); m = MEM.search(log)
    if r.returncode != 0:
        print("RC", r.returncode, log[-1500:]); sys.exit(2)
    return {
        "subject": subject, "arm": arm, "limit": limit, "wall": wall,
        "fold_s": float(f.group(3)) if f else None,
        "fold_per_frame_ms": 1000.0 * float(f.group(3)) / int(f.group(2)) if f else None,
        "folded_n": int(f.group(1)) if f else None,
        "workers": int(m.group(1)) if m else None,
        "align_how": a.group(1) if a else None,
        "align_s": float(a.group(4)) if a else None,
        "placed": int(a.group(2)) if a else None,
        "total_s": float(t.group(1)) if t else None,
    }

if __name__ == "__main__":
    plan = json.loads(sys.argv[1])   # [[subject, limit], ...]
    reps = int(sys.argv[2])
    tag = sys.argv[3]
    rows = []
    # warm the warpmap cache for every subject on BOTH arms first
    for subj, lim in plan:
        for arm in ("0", "1"):
            w = one(subj, arm, lim)
            print(f"warm {subj} n={lim} arm={arm}: align={w['align_how']} {w['align_s']}s "
                  f"fold={w['fold_s']}s workers={w['workers']}")
    for rep in range(reps):
        for subj, lim in plan:
            order = ("1", "0") if rep % 2 == 0 else ("0", "1")   # ABBA
            for arm in order:
                d = one(subj, arm, lim); d["rep"] = rep
                rows.append(d)
                print(f"rep{rep} {subj:22s} n={lim:3d} arm={arm} fold={d['fold_s']:7.2f}s "
                      f"({d['fold_per_frame_ms']:7.1f} ms/f) wall={d['wall']:7.2f}s "
                      f"align={d['align_how']}/{d['align_s']}s", flush=True)
    (OUT / f"timing-{tag}.json").write_text(json.dumps(rows, indent=1))
    print("\n=== SUMMARY (median of reps) ===")
    print(f"{'subject':24s} {'n':>4s} {'fold ms/f g0':>13s} {'fold ms/f g1':>13s} {'delta':>9s} {'delta%':>8s}")
    for subj, lim in plan:
        r0 = [r["fold_per_frame_ms"] for r in rows if r["subject"] == subj and r["arm"] == "0"]
        r1 = [r["fold_per_frame_ms"] for r in rows if r["subject"] == subj and r["arm"] == "1"]
        m0, m1 = statistics.median(r0), statistics.median(r1)
        print(f"{subj:24s} {lim:4d} {m0:13.1f} {m1:13.1f} {m1-m0:+9.1f} {100*(m1-m0)/m0:+8.2f}")
        print(f"{'  raw g0':24s} {'':4s} " + " ".join(f"{v:.1f}" for v in r0))
        print(f"{'  raw g1':24s} {'':4s} " + " ".join(f"{v:.1f}" for v in r1))
