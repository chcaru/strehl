"""Render arm matrix for V-BANDFLOOR. Writes masters + captures the banner.

Each (subject, arm) is one strehl invocation. Arms differ ONLY by the
STREHL_GATE_FLOOR_SCALE environment variable; every other flag is identical,
so any output difference is attributable to the knob alone.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR"

ARMS = {
    "A-unset": None,
    "N-null": "1,1,1,1,1,1,1",
    "B-coarse8": "1,8,8,8,8,8,8",
}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def render(subject, arm, force=False):
    out = os.path.join(OUT, "%s__%s.tiff" % (subject, arm))
    log = os.path.join(OUT, "%s__%s.log" % (subject, arm))
    if os.path.exists(out) and not force:
        print("SKIP (exists) %s" % out, flush=True)
        return out
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
    if ARMS[arm] is not None:
        env["STREHL_GATE_FLOOR_SCALE"] = ARMS[arm]
    cmd = [EXE, "stack", os.path.join(SRC, subject), "-o", out, "--srgb"]
    t0 = time.time()
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="replace")
    dt = time.time() - t0
    with open(log, "w", encoding="utf-8") as f:
        f.write("CMD: %s\nENV STREHL_GATE_FLOOR_SCALE=%r\nRC=%d ELAPSED=%.1f\n" % (
            " ".join(cmd), ARMS[arm], r.returncode, dt))
        f.write("---STDERR---\n" + r.stderr + "\n---STDOUT---\n" + r.stdout)
    if r.returncode != 0:
        print("FAIL rc=%d %s %s" % (r.returncode, subject, arm), flush=True)
        print(r.stderr[-2000:], flush=True)
        return None
    print("OK %-32s %-10s %6.1fs" % (subject, arm, dt), flush=True)
    for line in r.stderr.splitlines():
        if line.startswith(("averaged", "measured floor", "tone ", "exposure")):
            print("     " + line.rstrip(), flush=True)
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for spec in sys.argv[1:]:
        subj, arm = spec.split("@")
        jobs.append((subj, arm))
    res = {}
    for subj, arm in jobs:
        p = render(subj, arm)
        if p:
            res["%s@%s" % (subj, arm)] = sha256(p)
            print("     sha256 %s" % res["%s@%s" % (subj, arm)][:32], flush=True)
    print(json.dumps(res, indent=1), flush=True)
