"""Render each ARM on the two disjoint split-halves, so sigref.py can
decompose signal vs noise per arm."""
import hashlib
import os
import subprocess
import sys

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"

ARMS = {"B-coarse8": "1,8,8,8,8,8,8",
        "D2": "2,1,1,1,1,1,1",
        "D4": "4,1,1,1,1,1,1",
        "C-fine8": "8,1,1,1,1,1,1"}


def run(indir, name, val):
    dst = os.path.join(OUT, "%s.tiff" % name)
    if os.path.exists(dst):
        print("  skip %s" % name, flush=True)
        return
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
    if val:
        env["STREHL_GATE_FLOOR_SCALE"] = val
    p = subprocess.run([EXE, "stack", indir, "-o", dst, "--linear-srgb"],
                       capture_output=True, text=True, env=env)
    log = p.stdout + p.stderr
    open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(log)
    avg = ""
    for line in log.splitlines():
        if line.strip().startswith("averaged"):
            avg = line.split(":", 1)[1].strip()
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper() if p.returncode == 0 else "FAIL"
    print("  %-34s %s  averaged %s" % (name, h[:16], avg), flush=True)


for subject in sys.argv[1:]:
    for lbl in ("EVEN", "ODD"):
        d = os.path.join(STAGE, "%s__%s" % (subject, lbl))
        assert os.path.isdir(d), d
        for arm, val in ARMS.items():
            run(d, "%s__%s__%s" % (subject, lbl, arm), val)
