"""Two-sided commissioning of grade.py's tone-curve guard.

Rule earned the hard way: a guard that has only ever passed is not a guard.
The mutation is anchored on a UNIQUE FULL LINE and this script hard-errors
if the anchor does not land, so a silent no-op cannot read as a pass.
Regression is done from a $TEMP pin, never `git checkout --`.
"""
import os, shutil, subprocess, sys, tempfile, time

SRC = os.path.join("experiments", "ORCH-drift-check", "grade.py")
PROBE = os.path.join(tempfile.gettempdir(), "grade_guard_probe.py")
PIN = os.path.join(tempfile.gettempdir(), "grade_pin.py")

ANCHOR = "    return x + S_CURVE_STRENGTH * x * (1.0 - x) * (2.0 * x - 1.0)\n"
MUTANT = "    return x + S_CURVE_STRENGTH * x * (1.0 - x) * (2.0 * x - 1.0) * -1.0\n"

with open(PROBE, "w", encoding="utf-8") as f:
    f.write("import sys\n"
            "sys.path.insert(0, r'%s')\n"
            "import grade\n"
            "grade.assert_is_an_s_curve()\n"
            "print('GUARD PASSED')\n" % os.path.abspath(os.path.dirname(SRC)))

def run():
    for p in list(sys.path):
        pass
    env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, PROBE], capture_output=True, text=True, env=env)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout+r.stderr).strip() else ""

original = open(SRC, encoding="utf-8").read()
shutil.copyfile(SRC, PIN)
print(f"pinned to {PIN}")

if original.count(ANCHOR) != 1:
    raise SystemExit(f"ANCHOR NOT FOUND EXACTLY ONCE (count={original.count(ANCHOR)}) - "
                     "refusing to report; the mutation would have been a silent no-op")
print("anchor located exactly once\n")

rc, msg = run()
print(f"ARM A  as fixed      rc={rc}  {msg}")
armA = (rc == 0)

open(SRC, "w", encoding="utf-8").write(original.replace(ANCHOR, MUTANT))
os.utime(SRC, None)
rc, msg = run()
print(f"ARM B  sign restored rc={rc}  {msg}")
armB = (rc != 0)

shutil.copyfile(PIN, SRC)
os.utime(SRC, None)
rc, msg = run()
print(f"ARM C  restored      rc={rc}  {msg}")
armC = (rc == 0)
assert open(SRC, encoding="utf-8").read() == original, "RESTORE FAILED - file differs from pin"
print("restore byte-verified against the pin\n")

ok = armA and armB and armC
print(f"A pass={armA}  B fails={armB}  C pass={armC}")
print("COMMISSIONED: the guard fires on the real defect" if ok else "NOT COMMISSIONED")
sys.exit(0 if ok else 1)
