"""Extend ORCH's band-0 ladder upward to 6x and 8x as requested, plus the
linear split-half renders needed to qualify each band on the MERGED master."""
import hashlib
import os
import subprocess

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro\112MSDCF"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\bf112"


def run(indir, name, val, mode):
    dst = os.path.join(OUT, "%s.tiff" % name)
    if os.path.exists(dst):
        print("  skip %s" % name, flush=True)
        return
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
    if val:
        env["STREHL_GATE_FLOOR_SCALE"] = val
    p = subprocess.run([EXE, "stack", indir, "-o", dst, mode],
                       capture_output=True, text=True, env=env)
    log = p.stdout + p.stderr
    open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(log)
    avg = ""
    for line in log.splitlines():
        if line.strip().startswith("averaged"):
            avg = line.split(":", 1)[1].strip()
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper() if p.returncode == 0 else "FAIL"
    print("  %-26s %s  averaged %s" % (name, h[:16], avg), flush=True)


for nm, v in (("F6", "6,1,1,1,1,1,1"), ("F8", "8,1,1,1,1,1,1")):
    run(SRC, "srgb__%s" % nm, v, "--srgb")
for nm, v in (("F6", "6,1,1,1,1,1,1"), ("F8", "8,1,1,1,1,1,1")):
    run(SRC, "lin__%s" % nm, v, "--linear-srgb")
for lbl in ("EVEN", "ODD"):
    d = os.path.join(STAGE, "112MSDCF__%s" % lbl)
    run(d, "112MSDCF__%s__F8" % lbl, "8,1,1,1,1,1,1", "--linear-srgb")
