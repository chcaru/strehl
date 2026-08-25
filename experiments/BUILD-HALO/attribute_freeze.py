"""Attribute the byte-freeze break by ISOLATING THE VARIABLE, not by blaming a commit.

Both coffee-bean rows were baselined at 9695b3c and both have moved.  The
tempting inference is "my edge-aware default landed in between, so it must be
mine".  That is the reasoning this registry's own header calls out: a hash moved
for *a* reason, not necessarily *that* reason.

So: render each row's exact recorded invocation with the CURRENT binary and
STREHL_EDGE_AWARE=0.  If the old hash comes back, the edge-aware default is the
ENTIRE delta and nothing else that landed since 9695b3c touched these bytes.
If it does not come back, some of the delta belongs to someone else and I must
not sign for it.

This is strictly stronger than building a pin of my parent commit, which would
only show that the bytes differ across a commit boundary -- it could not tell
my change apart from anything else in the same range.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

EXE = Path(r"C:\dev\blog\death-of-software\projects\strehl\target\release\strehl.exe")
STACK = Path(r"D:\personal\macro\coffee-bean")
DATA = Path(r"C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli\tests\data")
OUT = Path(r"C:\dev\strehl-out\FREEZE-ATTR")

RENDER_ENV = [
    "STREHL_ALIGN", "STREHL_WARPMAP", "STREHL_CACHE_DIR",
    "STREHL_FIX_HALO", "STREHL_FIX_HALO_DELTA",
    "STREHL_EDGE_AWARE", "STREHL_EDGE_TAU", "STREHL_EDGE_CONF", "STREHL_ONLY_FRAME",
]

ROWS = [
    ("coffee-bean-20-gate2-unaligned",
     {"STREHL_ALIGN": "0"},
     "89958637A532E22DBB5476FD3467ACD1A9946A78B2829C503842B38DFC50C218"),
    ("coffee-bean-20-gate2-sidecar",
     {"STREHL_WARPMAP": str(DATA / "coffee-bean-20.warpmap.txt")},
     "2DB8A978D029EBF1B48474021CE28B15F4046A7509D29EAD42C935829AB446E5"),
]

OUT.mkdir(parents=True, exist_ok=True)
if not EXE.exists():
    sys.exit(f"no binary at {EXE} -- cargo build --release -p strehl-cli first")
if not STACK.is_dir():
    sys.exit(f"no capture dir at {STACK}")

results = []
for rid, extra, old in ROWS:
    scratch = OUT / f"{rid}-cache"
    scratch.mkdir(parents=True, exist_ok=True)
    tif = OUT / f"{rid}-armoff.tif"

    env = dict(os.environ)
    for k in RENDER_ENV:
        env.pop(k, None)
    env.update(extra)
    env["STREHL_CACHE_DIR"] = str(scratch)
    env["STREHL_EDGE_AWARE"] = "0"          # the variable under test

    argv = [str(EXE), "stack", str(STACK),
            "--limit", "20", "--gate", "2.0", "--out", str(tif)]

    print(f"\n=== {rid}  (STREHL_EDGE_AWARE=0) ===", flush=True)
    p = subprocess.run(argv, env=env, capture_output=True)
    if p.returncode != 0:
        print(p.stderr.decode("utf-8", "replace")[-2500:])
        sys.exit(f"render failed for {rid}")

    got = hashlib.sha256(tif.read_bytes()).hexdigest().upper()
    same = got == old
    results.append((rid, same))
    print(f"  old baseline : {old}")
    print(f"  arm-off now  : {got}")
    print(f"  -> {'REPRODUCED — delta is entirely the edge-aware default' if same else 'DID NOT REPRODUCE — something else also moved these bytes'}")

print("\n================ ATTRIBUTION ================")
for rid, same in results:
    print(f"  {rid:<34} {'MINE (proven)' if same else 'NOT SOLELY MINE'}")
if all(s for _, s in results):
    print("\nAll rows reproduce their pre-change baseline with my arm off.")
    print("The edge-aware default accounts for the whole delta.")
else:
    print("\nAt least one row does NOT reproduce. Do not sign for that row.")
