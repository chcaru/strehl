"""Stage and render EVEN/ODD split-half pairs for GENERALISATION of the
flat-site reproducibility finding beyond 119MSDCF.

Same construction as ladder.py used for 119MSDCF: disjoint alternating frame
subsets, matched focus range (both span end to end), arm A-unset (shipping
default), recipe `stack <dir> -o <out> --linear-srgb`.
"""
import hashlib
import os
import shutil
import subprocess
import sys

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"


def run(indir, name):
    dst = os.path.join(OUT, "%s.tiff" % name)
    if os.path.exists(dst):
        print("  skip %s" % name, flush=True)
        return
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
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
    fs = sorted(f for f in os.listdir(os.path.join(SRC, subject)) if f.upper().endswith(".ARW"))
    for par, lbl in ((0, "EVEN"), (1, "ODD")):
        d = os.path.join(STAGE, "%s__%s" % (subject, lbl))
        os.makedirs(d, exist_ok=True)
        picked = [f for i, f in enumerate(fs) if i % 2 == par]
        for f in picked:
            if not os.path.exists(os.path.join(d, f)):
                shutil.copy2(os.path.join(SRC, subject, f), os.path.join(d, f))
        print("staged %s %s n=%d first=%s last=%s" % (subject, lbl, len(picked), picked[0], picked[-1]), flush=True)
        run(d, "%s__%s__A-unset" % (subject, lbl))
