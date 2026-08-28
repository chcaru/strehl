"""Full-resolution LINEAR split-halves, so each of ORCH's bands can be
qualified on the MERGED MASTER at ORCH's own resolution and band edges.

--srgb turns --demosaic ON BY DEFAULT (the tool's help says so), and the help
also says "Do not measure resolution on it". ORCH's band 0 and band 1 are the
two finest octaves of exactly such a render. --linear-srgb --demosaic gives the
same sampling grid with NO transfer curve, which is the space the help calls
"THE MODE TO MEASURE IN".
"""
import hashlib
import os
import subprocess

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro\112MSDCF"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\bf112"


def run(indir, name, val):
    dst = os.path.join(OUT, "%s.tiff" % name)
    if os.path.exists(dst):
        print("  skip %s" % name, flush=True)
        return
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
    if val:
        env["STREHL_GATE_FLOOR_SCALE"] = val
    p = subprocess.run([EXE, "stack", indir, "-o", dst, "--linear-srgb", "--demosaic"],
                       capture_output=True, text=True, env=env)
    log = p.stdout + p.stderr
    open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(log)
    avg = ""
    for line in log.splitlines():
        if line.strip().startswith("averaged"):
            avg = line.split(":", 1)[1].strip()
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper() if p.returncode == 0 else "FAIL"
    print("  %-30s %s  averaged %s" % (name, h[:16], avg), flush=True)


for lbl in ("EVEN", "ODD"):
    d = os.path.join(STAGE, "112MSDCF__%s" % lbl)
    for nm, v in (("A-unset", None), ("F4", "4,1,1,1,1,1,1")):
        run(d, "lindm__112MSDCF__%s__%s" % (lbl, nm), v)
for nm, v in (("A-unset", None), ("F4", "4,1,1,1,1,1,1")):
    run(SRC, "lindm__%s" % nm, v)
