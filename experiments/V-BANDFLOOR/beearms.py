"""B-coarse8 (ORCH's arm) and D4 (band-0 representative) on the bee-2-cpl
split-halves -- the deep subject ORCH named as make-or-break."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util
spec = importlib.util.spec_from_file_location("m", os.path.join(HERE, "sh2arm.py"))

STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
ARMS = {"B-coarse8": "1,8,8,8,8,8,8", "D4": "4,1,1,1,1,1,1"}

import hashlib, subprocess                                          # noqa: E402
EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"


def run(indir, name, val):
    dst = os.path.join(OUT, "%s.tiff" % name)
    if os.path.exists(dst):
        print("  skip %s" % name, flush=True)
        return
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
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
