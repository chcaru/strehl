"""Move round-2 output to a `rho2-` prefix and restore the round-1 `rho-*.txt`
evidence I overwrote by reusing the prefix.

Git blobs are read as bytes through subprocess rather than shell redirection:
`git show HEAD:path > file` in PowerShell re-encodes the stream and silently
corrupts the very evidence this is trying to restore.
"""

import pathlib
import subprocess
import sys

OUT = pathlib.Path("experiments/M90-prnu/out")

# Round-1 files that live at these names in HEAD.
R1 = [
    "rho-109MSDCF.txt",
    "rho-bee-3-cpl.txt",
    "rho-coffee-bean.txt",
    "rho-foam.txt",
]

moved = []
for p in sorted(OUT.glob("rho-*.txt")):
    dst = OUT / ("rho2-" + p.name[len("rho-") :])
    dst.write_bytes(p.read_bytes())
    moved.append((p.name, dst.name))

for name in R1:
    path = OUT / name
    blob = subprocess.run(
        ["git", "show", f"HEAD:experiments/M90-prnu/out/{name}"],
        capture_output=True,
        check=True,
    ).stdout
    path.write_bytes(blob)
    print(f"restored {name} from HEAD ({len(blob)} bytes)")

for p in sorted(OUT.glob("rho-*.txt")):
    if p.name not in R1:
        p.unlink()
        print(f"removed stray round-2 name {p.name}")

print()
for a, b in moved:
    print(f"round-2 output {a} -> {b}")

# Verify: every restored file must now be byte-identical to HEAD.
bad = 0
for name in R1:
    blob = subprocess.run(
        ["git", "show", f"HEAD:experiments/M90-prnu/out/{name}"],
        capture_output=True,
        check=True,
    ).stdout
    if (OUT / name).read_bytes() != blob:
        print(f"MISMATCH {name}")
        bad += 1
print(f"\nrestored files matching HEAD: {len(R1) - bad}/{len(R1)}")
sys.exit(1 if bad else 0)
