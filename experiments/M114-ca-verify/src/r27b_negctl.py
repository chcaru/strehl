"""M114 r27b -- negative control for the report verifier.

A verifier that has only ever returned green is an untested instrument. This
plants three defects, one per check class, and requires r27 to go RED on each.

Each mutation is anchored on a unique FULL string and hard-errors if it does not
land, so a silently-missed mutation cannot be scored as a caught one. The report
is backed up to TEMP and restored from that copy -- never via git checkout.
"""
import io
import os
import shutil
import subprocess
import sys

REP = r"docs\research\M114-ca-verify.md"
BAK = os.path.join(os.environ["TEMP"], "M114-ca-verify.md.bak")
VER = [sys.executable, r"experiments\M114-ca-verify\src\r27_verify_report.py"]

MUT = [
    ("leak table cell",
     "| green -> red | **27.4206** | 10.4395 |",
     "| green -> red | **27.4216** | 10.4395 |"),
    ("r26b table cell",
     "| `specular` | **3 / 8** | **242.13 px** |",
     "| `specular` | **3 / 8** | **242.14 px** |"),
    ("prose tif count",
     "All **23** TIFFs read by M114 probes are genuinely `uint16`",
     "All **24** TIFFs read by M114 probes are genuinely `uint16`"),
]

shutil.copyfile(REP, BAK)
print("backed up ->", BAK)


def run():
    p = subprocess.run(VER, capture_output=True, text=True)
    return p.returncode, p.stdout


rc, out = run()
print("baseline: rc=%d  %s" % (rc, out.strip().splitlines()[-1]))
if rc != 0:
    shutil.copyfile(BAK, REP)
    sys.exit("baseline is not green; aborting")

caught = 0
for label, old, new in MUT:
    s = io.open(REP, encoding="utf-8").read()
    if s.count(old) != 1:
        shutil.copyfile(BAK, REP)
        sys.exit("MUTATION TARGET NOT FOUND (%d occurrences): %s" % (s.count(old), label))
    io.open(REP, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
    rc, out = run()
    last = out.strip().splitlines()[-1]
    ok = rc != 0
    caught += ok
    print("  %-18s planted -> rc=%d  %-22s  %s" % (label, rc, last, "RED (caught)" if ok else "*** GREEN, MISSED ***"))
    shutil.copyfile(BAK, REP)

rc, out = run()
print("restored: rc=%d  %s" % (rc, out.strip().splitlines()[-1]))
print()
print("%d/%d planted defects caught; verifier %s"
      % (caught, len(MUT), "COMMISSIONED" if caught == len(MUT) and rc == 0 else "NOT COMMISSIONED"))
sys.exit(0 if (caught == len(MUT) and rc == 0) else 1)
