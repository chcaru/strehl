"""Band-0 ladder, combined ladder, and a SPLIT-HALF test of whether the flat
sites are genuinely flat at band-0 frequencies.

SPLIT-HALF. The orchestrator's first failure mode is that flat sites may carry
REAL texture at band-0 frequencies, in which case selection there is correct and
the grain rise is not a defect. Real texture is REPRODUCIBLE across independent
frame subsets of the same scene; noise is INDEPENDENT. So render the even-index
frames and the odd-index frames as two disjoint stacks at matched focus range
and correlate their band-0 content site by site. High correlation = real
texture. Near-zero = the band-0 content there is noise, and selecting on it is
selecting on noise.
"""
import hashlib
import os
import shutil
import subprocess

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"

LADDER = {
    "D2": "2,1,1,1,1,1,1",     # band 0 alone, x2
    "D4": "4,1,1,1,1,1,1",     # band 0 alone, x4
    "E4": "4,8,8,8,8,8,8",     # combined, band0 x4 + coarse tail 8
    "E8": "8,8,8,8,8,8,8",     # all bands x8
}
JOBS = [("119MSDCF", 33, os.path.join(SRC, "119MSDCF")),
        ("119MSDCF", 17, os.path.join(STAGE, "119MSDCF__N17")),
        ("113MSDCF", 63, os.path.join(SRC, "113MSDCF")),
        ("113MSDCF", 32, os.path.join(STAGE, "113MSDCF__N32"))]


def run(indir, name, val, extra=()):
    dst = os.path.join(OUT, "%s.tiff" % name)
    if os.path.exists(dst):
        print("  skip %s" % name, flush=True)
        return
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
    if val:
        env["STREHL_GATE_FLOOR_SCALE"] = val
    p = subprocess.run([EXE, "stack", indir, "-o", dst, "--linear-srgb"] + list(extra),
                       capture_output=True, text=True, env=env)
    log = p.stdout + p.stderr
    open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(log)
    avg = ""
    for line in log.splitlines():
        if line.strip().startswith("averaged"):
            avg = line.split(":", 1)[1].strip()
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper() if p.returncode == 0 else "FAIL"
    print("  %-34s %s  averaged %s" % (name, h[:16], avg), flush=True)


# ---- split-half staging on 119MSDCF (arm A-unset, the shipping default)
fs = sorted(f for f in os.listdir(os.path.join(SRC, "119MSDCF")) if f.upper().endswith(".ARW"))
for par, lbl in ((0, "EVEN"), (1, "ODD")):
    d = os.path.join(STAGE, "119MSDCF__%s" % lbl)
    os.makedirs(d, exist_ok=True)
    picked = [f for i, f in enumerate(fs) if i % 2 == par]
    for f in picked:
        if not os.path.exists(os.path.join(d, f)):
            shutil.copy2(os.path.join(SRC, "119MSDCF", f), os.path.join(d, f))
    print("staged %s n=%d first=%s last=%s" % (lbl, len(picked), picked[0], picked[-1]), flush=True)
    run(d, "119MSDCF__%s__A-unset" % lbl, None)

for subject, n, d in JOBS:
    for arm, val in LADDER.items():
        run(d, "%s__N%d__%s" % (subject, n, arm), val)
