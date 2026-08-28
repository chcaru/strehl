"""Recipe check for the N-scaling work: --linear-srgb, pyramid backend, null byte-identity.

The tool's own help says --srgb is NOT the mode to measure in ("the transfer
curve is a strong non-linearity that moves every ratio a metric computes").
Everything from here uses --linear-srgb. This confirms (a) the backend is the
pyramid, (b) the tone stage is absent, (c) the commissioned null 1,1,1,1,1,1,1
is still byte-identical to unset under the NEW recipe -- byte-identity under
--srgb does not entail it under --linear-srgb and must be re-established.
"""
import hashlib
import os
import subprocess

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\lin"
os.makedirs(OUT, exist_ok=True)

ARMS = {"A-unset": None, "N-null": "1,1,1,1,1,1,1", "B-coarse8": "1,8,8,8,8,8,8"}
SUB = r"D:\personal\macro\coffee-bubbles"

for arm, val in ARMS.items():
    dst = os.path.join(OUT, "coffee-bubbles__%s.tiff" % arm)
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
    if val is not None:
        env["STREHL_GATE_FLOOR_SCALE"] = val
    p = subprocess.run([EXE, "stack", SUB, "-o", dst, "--linear-srgb"],
                       capture_output=True, text=True, env=env)
    log = p.stdout + p.stderr
    open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(log)
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper()
    print("=== %s  rc=%d  sha=%s" % (arm, p.returncode, h[:32]))
    for line in log.splitlines():
        s = line.strip()
        if s.startswith(("merge", "backend", "tone", "averaged", "measured floor",
                         "output", "clip", "exposure", "gate floor")):
            print("    " + s)
