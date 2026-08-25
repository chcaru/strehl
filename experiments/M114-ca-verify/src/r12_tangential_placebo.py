"""M114 r12: the TANGENTIAL PLACEBO arm (ORCH's resampler control).

The `zero` arm is void as a resampler control: fact 1517 shows it is
byte-identical to `off` because `compose` short-circuits at zero strength and
never resamples. The placebo here multiplies by the COMPLEX (1 + i*eps) instead
of the real (1 + eps): identical displacement magnitude |eps|*r at every point,
rotated 90 degrees, same gather, same kernel, same resampled sensel count, and
ZERO radial correction. If the visible improvement is interpolation blur, this
arm reproduces it. If it is CA correction, this arm does not.

BARS
  N1  This binary's `off`  == E400A63A...  (cross-binary null, THIRD binary)
  N2  This binary's `on`   == E9580E8A...  (proves the patch is INERT on the
      shipped path; without this the placebo build could be measuring itself)
  P1  `tan` != `off`   RED IF EQUAL: the placebo did not resample and the arm
      is void, exactly as `zero` is void.
  P2  `tan` != `on`
Exit codes come from subprocess.run().returncode, never $LASTEXITCODE.
"""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\target-tan\release\strehl.exe")
DIR = Path(r"D:\personal\macro\bee-3-cpl")
OUT = Path(r"C:\dev\strehl-out\M114-ca-verify\r12")
SIDE = Path(r"C:\dev\strehl-out\M114-ca-verify\r1\m114-warpmap.txt")
KEY = "a7c2-fe100gm-2xtc-x4cpl"
TAN = "a7c2-fe100gm-2xtc-x4cpl-tangential-placebo"
OFF_HASH = "E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112"
ON_HASH = "E9580E8A2A85009494B2FE5A35441EBE5D5F9F7E6B80ADBD079B40130B7742E9"
OUT.mkdir(parents=True, exist_ok=True)

assert SIDE.exists(), "frozen sidecar missing: " + str(SIDE)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest().upper()

res = {}
for name, val in [("off", "0"), ("on", KEY), ("tan", TAN)]:
    tif = OUT / (name + ".tif")
    env = dict(os.environ)
    env.pop("STREHL_FIX_CA", None)
    env["STREHL_WARPMAP"] = str(SIDE)
    env["STREHL_FIX_CA"] = val
    t0 = time.time()
    p = subprocess.run([str(EXE), "stack", str(DIR), "--srgb", "--auto-exposure",
                        "-o", str(tif)], capture_output=True, text=True, env=env)
    dt = time.time() - t0
    if p.returncode != 0:
        print((p.stdout + p.stderr)[-3000:])
        sys.exit("RENDER FAILED for arm " + name)
    res[name] = sha(tif)
    print("%-4s exit=%d %5.1fs  %s" % (name, p.returncode, dt, res[name]))

n1 = res["off"] == OFF_HASH
n2 = res["on"] == ON_HASH
p1 = res["tan"] != res["off"]
p2 = res["tan"] != res["on"]
print("\nN1 off reproduces the pre-wiring hash (3rd binary) : %s" % ("PASS" if n1 else "FAIL"))
print("N2 on  reproduces M107's hash (patch is inert)     : %s" % ("PASS" if n2 else "FAIL"))
print("P1 tan DIFFERS from off (placebo really resampled) : %s" % ("PASS" if p1 else "FAIL -- ARM VOID"))
print("P2 tan DIFFERS from on                             : %s" % ("PASS" if p2 else "FAIL"))
(OUT / "r12.json").write_text(json.dumps(
    {"hashes": res, "N1": n1, "N2": n2, "P1": p1, "P2": p2}, indent=1), encoding="utf-8")
