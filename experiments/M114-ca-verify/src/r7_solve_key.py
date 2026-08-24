"""M114 R7 -- does STREHL_FIX_CA change the SOLVE?  A direct falsification.

M107 claims CA must NOT be in SOLVE_ENV because the solve cannot read it.
The call graph says so; this asks the binary.

  K1  solve the warp map twice, once with STREHL_FIX_CA unset and once with it
      set to the profile key, and compare the sidecars BYTE FOR BYTE (ignoring
      nothing).  If they differ, M107 is wrong and the key must include CA.
  K2  control that K1 can go red: solve a third time with --reference changed
      by one.  That MUST produce a different sidecar, proving the comparison
      is capable of detecting a changed solve.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

EXE = r"C:\dev\strehl-out\M114-ca-verify\cargo-target\release\strehl.exe"
DIR = r"D:\personal\macro\bee-3-cpl"
OUT = Path(r"C:\dev\strehl-out\M114-ca-verify\r7")
OUT.mkdir(parents=True, exist_ok=True)
KEY = "a7c2-fe100gm-2xtc-x4cpl"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()


def align(name, ca, ref):
    out = OUT / (name + ".txt")
    env = dict(os.environ)
    env.pop("STREHL_FIX_CA", None)
    env.pop("STREHL_WARPMAP", None)
    if ca is not None:
        env["STREHL_FIX_CA"] = ca
    p = subprocess.run([EXE, "align", DIR, "--out", str(out),
                        "--reference", str(ref)],
                       capture_output=True, text=True, env=env)
    print("  align %-12s CA=%-26r ref=%d EXIT=%d" % (name, ca, ref, p.returncode))
    if p.returncode != 0:
        print(p.stdout[-1500:], p.stderr[-1500:])
        sys.exit("align failed")
    return sha(out), out


a, pa = align("ca_off", None, 149)
b, pb = align("ca_on", KEY, 149)
c, pc = align("ref_148", None, 148)
print()
print("  ca_off  sha256 =", a)
print("  ca_on   sha256 =", b)
print("  ref_148 sha256 =", c)
k1 = (a == b)
k2 = (a != c)
print("K1 CA does not change the solved sidecar : %s" % ("PASS" if k1 else "FAIL"))
print("K2 control -- reference DOES change it   : %s" % ("PASS" if k2 else "FAIL -- instrument is blind"))
