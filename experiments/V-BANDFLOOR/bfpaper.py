"""Paper focus-sweep (ORCH's 6th subject) -- ladder + split-halves.

ORCH asks me to treat this as a fine-texture stress test, not a null.
Three sets:
  1. --srgb ladder 1..64  : ORCH's recipe, scored on the COMMITTED contrast_ms.py
  2. --linear-srgb        : no tone stage, for clip and level work
  3. --linear-srgb EVEN/ODD split-halves : sigref decides SIGNAL vs NOISE by
     reproducibility across disjoint frame sets. This is the ground truth that
     ORCH's energy-vs-scale SLOPE heuristic must be checked against.
"""
import hashlib
import os
import shutil
import subprocess

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro\flat-fields\subject-focus-sweep-with-cpl"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\paper"
os.makedirs(OUT, exist_ok=True)

LADDER = [("A-unset", None), ("F2", "2,1,1,1,1,1,1"), ("F4", "4,1,1,1,1,1,1"),
          ("F8", "8,1,1,1,1,1,1"), ("F16", "16,1,1,1,1,1,1"),
          ("F32", "32,1,1,1,1,1,1"), ("F64", "64,1,1,1,1,1,1")]

HASHES = {}


def run(indir, name, val, mode):
    dst = os.path.join(OUT, "%s.tiff" % name)
    if not os.path.exists(dst):
        env = dict(os.environ)
        env.pop("STREHL_GATE_FLOOR_SCALE", None)
        if val:
            env["STREHL_GATE_FLOOR_SCALE"] = val
        p = subprocess.run([EXE, "stack", indir, "-o", dst, mode],
                           capture_output=True, text=True, env=env)
        open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(p.stdout + p.stderr)
    log = open(dst.replace(".tiff", ".log"), encoding="utf-8").read()
    avg = ""
    for line in log.splitlines():
        if line.strip().startswith("averaged"):
            avg = line.split(":", 1)[1].strip()
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper()
    HASHES.setdefault(h, []).append(name)
    print("  %-24s %s  averaged %s" % (name, h[:16], avg[:46]), flush=True)


print("=== SET 1: --srgb ladder 1,2,4,8,16,32,64 ===", flush=True)
for nm, v in LADDER:
    run(SRC, "srgb__%s" % nm, v, "--srgb")

print("=== SET 2: --linear-srgb ladder ===", flush=True)
for nm, v in LADDER:
    run(SRC, "lin__%s" % nm, v, "--linear-srgb")

print("=== SET 3: --linear-srgb split-halves for sigref ===", flush=True)
fs = sorted(f for f in os.listdir(SRC) if f.upper().endswith(".ARW"))
for par, lbl in ((0, "EVEN"), (1, "ODD")):
    d = os.path.join(STAGE, "paper__%s" % lbl)
    os.makedirs(d, exist_ok=True)
    picked = [f for i, f in enumerate(fs) if i % 2 == par]
    for f in picked:
        if not os.path.exists(os.path.join(d, f)):
            shutil.copy2(os.path.join(SRC, f), os.path.join(d, f))
    print("staged %s n=%d first=%s last=%s" % (lbl, len(picked), picked[0], picked[-1]), flush=True)
    for nm, v in (("A-unset", None), ("F4", "4,1,1,1,1,1,1"), ("F16", "16,1,1,1,1,1,1")):
        run(d, "paper__%s__%s" % (lbl, nm), v, "--linear-srgb")

print("=== FILENAME-COLLISION GUARD (ORCH's $s.tiff trap) ===", flush=True)
dup = {h: n for h, n in HASHES.items() if len(n) > 1}
if dup:
    for h, n in dup.items():
        print("  COLLISION %s -> %s" % (h[:16], n), flush=True)
else:
    print("  all %d renders have distinct SHA-256: no rung overwrote another"
          % len(HASHES), flush=True)
