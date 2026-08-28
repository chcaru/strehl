"""Stage decimated copies at MATCHED FOCUS RANGE, then render the arm matrix.

WHY DECIMATION AND NOT --limit. `--limit` takes the first L files in filename
order, which shortens the focus bracket: it confounds frame count with depth of
field, so any difference could be either. Decimation keeps the FIRST and LAST
frame and drops frames from the middle, so the focus range is identical by
construction and only the sampling density changes.

Index rule: round(i * (N-1) / (M-1)) for i in 0..M-1. i=0 -> 0 and i=M-1 -> N-1,
so both endpoints are always retained. Duplicates are impossible for M <= N.

Recipe is --linear-srgb: the tool's own help states --srgb is NOT the mode to
measure in because the transfer curve moves every ratio a metric computes.
--linear-srgb also emits NO tone stage, which removes the black/white-point
confound entirely.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"

# (subject, deep N == all frames, shallow N)
PLAN = [
    ("113MSDCF", 63, 32),                    # exact replication of the other lane
    ("coffee-bubbles", 19, 10),
    ("119MSDCF", 33, 17),
    ("leaf-2-cpl", 182, 91),                 # the claim subject
    ("bee-2-cpl", 299, 150),                 # the motivating deep case
    ("dry-erase-marker-head-cpl", 299, 150),
]
ARMS = {"A-unset": None, "B-coarse8": "1,8,8,8,8,8,8"}


def frames(subject):
    d = os.path.join(SRC, subject)
    return sorted(f for f in os.listdir(d) if f.upper().endswith(".ARW"))


def stage_decimated(subject, m):
    fs = frames(subject)
    n = len(fs)
    idx = [round(i * (n - 1) / (m - 1)) for i in range(m)]
    assert len(set(idx)) == m, "duplicate index"
    assert idx[0] == 0 and idx[-1] == n - 1, "focus range not matched"
    d = os.path.join(STAGE, "%s__N%d" % (subject, m))
    os.makedirs(d, exist_ok=True)
    for i in idx:
        dst = os.path.join(d, fs[i])
        if not os.path.exists(dst):
            shutil.copy2(os.path.join(SRC, subject, fs[i]), dst)
    have = [f for f in os.listdir(d) if f.upper().endswith(".ARW")]
    assert len(have) == m, "staged %d want %d" % (len(have), m)
    print("  staged %s N=%d (first=%s last=%s)" % (subject, m, fs[idx[0]], fs[idx[-1]]),
          flush=True)
    return d


def render(indir, tag, arm, val):
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "%s__%s.tiff" % (tag, arm))
    if os.path.exists(dst):
        print("  skip %s" % os.path.basename(dst), flush=True)
        return dst
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
    if val is not None:
        env["STREHL_GATE_FLOOR_SCALE"] = val
    p = subprocess.run([EXE, "stack", indir, "-o", dst, "--linear-srgb"],
                       capture_output=True, text=True, env=env)
    log = p.stdout + p.stderr
    open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(log)
    if p.returncode != 0:
        print("  FAIL rc=%d %s" % (p.returncode, tag), flush=True)
        return None
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper()
    avg = ""
    for line in log.splitlines():
        if line.strip().startswith("averaged"):
            avg = line.split(":", 1)[1].strip()
    print("  %-34s %s  averaged %s" % (os.path.basename(dst), h[:16], avg), flush=True)
    return dst


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    for subject, deep, shallow in PLAN:
        if only and subject not in only:
            continue
        print("=== %s  deep N=%d  shallow N=%d" % (subject, deep, shallow), flush=True)
        assert len(frames(subject)) == deep, "frame count changed"
        dirs = {deep: os.path.join(SRC, subject), shallow: stage_decimated(subject, shallow)}
        for n, d in dirs.items():
            for arm, val in ARMS.items():
                render(d, "%s__N%d" % (subject, n), arm, val)


if __name__ == "__main__":
    main()
