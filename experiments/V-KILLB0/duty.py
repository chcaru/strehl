"""V-KILLB0 duty.py -- band-0 'averaged' duty cycle per subject per arm.

Parsing rule ESTABLISHED FROM THE LOG STRUCTURE, not assumed: the harness line
"[N] subject ... ok=True" is emitted first and strehl's captured banner follows
it.  Verified two ways: the file's first content line is "[1] 112MSDCF" (so no
banner precedes any subject) and its last banner is followed only by
"=== finished" (so no banner trails the final subject).  Cross-check: this
mapping puts 112MSDCF default at 32.1% and b0x4 at 80.9%, which are exactly the
two numbers ORCH reported for that subject, so the mapping reproduces his
independent reading.

The duty cycle is the fraction of band-0 coefficients that fell BELOW the noise
gate and were averaged across frames instead of selected from the sharpest
frame.  Averaging a focus stack at a site that has real structure is a blur, so
a subject whose DEFAULT duty is already high has band-0 coefficients sitting
close to the floor even where there is structure -- exactly the condition under
which raising the floor cannot be self-targeting.
"""
import os
import re

OUT = r"C:\dev\strehl-out\V-KILLB0"
ARMS = ["default", "b0x2", "b0x4", "b0x8"]
SUBJ = re.compile(r"^\[(\d+)\]\s+(\S+)\s+frames=(\d+)")
AVG = re.compile(r"^\s+averaged\s+:\s+([\d.]+)%")
FLOOR = re.compile(r"^\s+measured floor\s+:\s+([\d.]+)")

data = {}
for arm in ARMS:
    p = os.path.join(OUT, arm, "render.log")
    if not os.path.exists(p):
        continue
    cur = None
    for line in open(p, encoding="utf-8", errors="replace"):
        m = SUBJ.match(line)
        if m:
            cur = m.group(2)
            data.setdefault(cur, {})["N"] = int(m.group(3))
            continue
        m = AVG.match(line)
        if m and cur:
            data[cur][arm] = float(m.group(1))
            cur_done = cur
        m = FLOOR.match(line)
        if m and cur:
            data[cur][arm + "_floor"] = float(m.group(1))

if data.get("112MSDCF", {}).get("default") != 32.1 or \
        data.get("112MSDCF", {}).get("b0x4") != 80.9:
    raise SystemExit("ANCHOR FAILED: 112MSDCF must read 32.1 -> 80.9 to match "
                     f"ORCH's own reading; got {data.get('112MSDCF')}")
print("anchor OK: 112MSDCF default=32.1% b0x4=80.9% (matches ORCH)\n")
print(f"{'subject':<26} {'N':>4} {'floor':>7} " + "".join(f"{a:>9}" for a in ARMS))
for s in sorted(data, key=lambda k: -data[k].get("default", -1)):
    d = data[s]
    row = "".join(f"{d[a]:8.1f}%" if a in d else f"{'-':>9}" for a in ARMS)
    print(f"{s:<26} {d['N']:4d} {d.get('default_floor', float('nan')):7.4f} {row}")
