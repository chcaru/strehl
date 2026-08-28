"""Extra arms: a DIRECT MECHANISM TEST plus a full-resolution control.

MECHANISM TEST. The measured N-scaling defect lives at BAND 0. The proposed arm
is 1,8,8,8,8,8,8, whose band-0 multiplier is 1 -- it leaves band 0 untouched by
construction, and the banner confirms band-0 duty cycle is bit-identical between
arms. If the mechanism diagnosis is right, then an arm that raises BAND 0
instead should move the primary metric where the proposed arm cannot. That is a
re-choice, not a re-computation: it can fail.

FULL-RESOLUTION CONTROL. --linear-srgb is BINNED, and binning averages 2x2 and
so destroys exactly the top-octave noise this mechanism is about. If my
magnitude disagrees with the other lane because of binning, the same subject
rendered with --demosaic must show a LARGER band-0 effect.
"""
import hashlib
import os
import subprocess

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
SRC = r"D:\personal\macro"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"

JOBS = [
    # subject,   N,  dir,                              arm,        env,             extra
    ("119MSDCF", 33, os.path.join(SRC, "119MSDCF"),     "C-fine8",  "8,1,1,1,1,1,1", []),
    ("119MSDCF", 17, os.path.join(STAGE, "119MSDCF__N17"), "C-fine8", "8,1,1,1,1,1,1", []),
    ("113MSDCF", 63, os.path.join(SRC, "113MSDCF"),     "C-fine8",  "8,1,1,1,1,1,1", []),
    ("113MSDCF", 32, os.path.join(STAGE, "113MSDCF__N32"), "C-fine8", "8,1,1,1,1,1,1", []),
    ("113MSDCF", 63, os.path.join(SRC, "113MSDCF"),     "FR-A",     None, ["--demosaic"]),
    ("113MSDCF", 32, os.path.join(STAGE, "113MSDCF__N32"), "FR-A",  None, ["--demosaic"]),
    ("113MSDCF", 63, os.path.join(SRC, "113MSDCF"),     "FR-B",  "1,8,8,8,8,8,8", ["--demosaic"]),
    ("113MSDCF", 32, os.path.join(STAGE, "113MSDCF__N32"), "FR-B", "1,8,8,8,8,8,8", ["--demosaic"]),
]

for subject, n, d, arm, val, extra in JOBS:
    dst = os.path.join(OUT, "%s__N%d__%s.tiff" % (subject, n, arm))
    if os.path.exists(dst):
        print("  skip %s" % os.path.basename(dst), flush=True)
        continue
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
    if val is not None:
        env["STREHL_GATE_FLOOR_SCALE"] = val
    p = subprocess.run([EXE, "stack", d, "-o", dst, "--linear-srgb"] + extra,
                       capture_output=True, text=True, env=env)
    log = p.stdout + p.stderr
    open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(log)
    avg = ""
    for line in log.splitlines():
        if line.strip().startswith("averaged"):
            avg = line.split(":", 1)[1].strip()
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper() if p.returncode == 0 else "FAIL"
    print("  %-32s %s  averaged %s" % (os.path.basename(dst), h[:16], avg), flush=True)
