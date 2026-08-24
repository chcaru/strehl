"""K14 -- verify the --reference default fix (fact 1370).

BARS, REGISTERED BEFORE THE RUN
-------------------------------
R1 DEFAULT IS THE MIDDLE. With no --reference on a 6-frame bracket, the tool
   announces `reference frame 3 (middle, default)` and the sidecar carries
   `reference 3`. 6/2 = 3 by merge_reference.

R2 POWER CONTROL -- the flag must still work. `--reference 0` must announce
   `reference frame 0 (--reference)` and write `reference 0`. Without this,
   R1 could be satisfied by a build that ignores the flag entirely, which
   would replace one trap with a worse one. This control can fail.

R3 THE RANGE GUARD SURVIVES. `--reference 6` on 6 frames exits non-zero. The
   guard now reads a resolved value rather than the raw arg, so it is genuinely
   re-plumbed and could have been lost.

R4 THE CHANGE IS NOT COSMETIC. R1's sidecar must DIFFER from R2's. If the two
   files are identical the reference does not affect the placements and the
   fix would be pointless. This is the arm that makes R1 mean something.

Nothing is written into D:\\personal\\macro: --out and STREHL_CACHE_DIR both
point into C:\\dev\\strehl-out\\M95-ref.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
EXE = ROOT / "target-m95" / "debug" / "strehl.exe"
STACK = Path(r"D:\personal\macro\bee-3-cpl")
SCRATCH = Path(r"C:\dev\strehl-out\M95-ref")
SCRATCH.mkdir(parents=True, exist_ok=True)

env = dict(os.environ)
env["STREHL_CACHE_DIR"] = str(SCRATCH / "cache")
env["PYTHONIOENCODING"] = "utf-8"


def align(tag, extra):
    out = SCRATCH / f"{tag}.warpmap.txt"
    if out.exists():
        out.unlink()
    cmd = [str(EXE), "align", str(STACK), "--limit", "6", "--out", str(out)] + extra
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or ""), out


print("=" * 78)
print("K14  --reference default (fact 1370)")
print("=" * 78)
print(f"exe   : {EXE}")
print(f"stack : {STACK}  --limit 6")
print(f"cache : {env['STREHL_CACHE_DIR']}  (capture library untouched)")

rc1, o1, f1 = align("default", [])
line1 = next((l.strip() for l in o1.splitlines() if "reference frame" in l), "<none>")
sc1 = f1.read_text(encoding="utf-8") if f1.exists() else ""
ref1 = re.search(r"^reference (\d+)", sc1, re.M)
ref1 = ref1.group(1) if ref1 else "<none>"
print(f"\nR1 default   rc={rc1}  announced: {line1!r}  sidecar reference {ref1}")

rc2, o2, f2 = align("ref0", ["--reference", "0"])
line2 = next((l.strip() for l in o2.splitlines() if "reference frame" in l), "<none>")
sc2 = f2.read_text(encoding="utf-8") if f2.exists() else ""
ref2 = re.search(r"^reference (\d+)", sc2, re.M)
ref2 = ref2.group(1) if ref2 else "<none>"
print(f"R2 --ref 0   rc={rc2}  announced: {line2!r}  sidecar reference {ref2}")

rc3, o3, _ = align("ref6", ["--reference", "6"])
err3 = next((l.strip() for l in o3.splitlines() if "out of range" in l), "<none>")
print(f"R3 --ref 6   rc={rc3}  {err3!r}")

r1 = rc1 == 0 and "reference frame 3 (middle, default)" in o1 and ref1 == "3"
r2 = rc2 == 0 and "reference frame 0 (--reference)" in o2 and ref2 == "0"
r3 = rc3 != 0 and "out of range" in o3
r4 = bool(sc1) and bool(sc2) and sc1 != sc2

print("\n--- BARS ---")
print(f"  R1 default is the middle (3)        {'PASS' if r1 else 'FAIL'}")
print(f"  R2 POWER: --reference still honoured {'PASS' if r2 else 'FAIL'}")
print(f"  R3 range guard survives             {'PASS' if r3 else 'FAIL'}")
print(f"  R4 the two sidecars differ          {'PASS' if r4 else 'FAIL'}")

def max_dx(sc):
    """Worst-case |dx| over placed frames -- the quantity the reference choice
    actually controls. Rows are `<idx> placed <bits...> # ... dx=<v> dy=<v>`."""
    vals = [abs(float(m.group(1)))
            for m in re.finditer(r"^\d+ placed .*dx=([-+0-9.e]+)", sc, re.M)]
    return (max(vals) if vals else float("nan")), len(vals)


if r4:
    d1, n1 = max_dx(sc1)
    d2, n2 = max_dx(sc2)
    print(f"     worst |dx|: reference 3 -> {d1:.4f} px over {n1} frames")
    print(f"                 reference 0 -> {d2:.4f} px over {n2} frames")
    print(f"     the old default cost {d2 / d1:.4f}x the worst-case displacement")
    res_dx = {"max_dx_ref3": d1, "max_dx_ref0": d2, "ratio": d2 / d1, "n": n1}
else:
    res_dx = {}

res = {"R1": r1, "R2": r2, "R3": r3, "R4": r4, "ref_default": ref1, "ref_flag": ref2,
       "announced_default": line1, "announced_flag": line2, "rc": [rc1, rc2, rc3],
       "displacement": res_dx}
(ROOT / "experiments" / "M95-kernel" / "out" / "k14_reference.json").write_text(
    json.dumps(res, indent=2), encoding="utf-8")
allp = r1 and r2 and r3 and r4
print(f"\nverdict: {'ALL PASS' if allp else 'FAILED'}")
sys.exit(0 if allp else 1)
