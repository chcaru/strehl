"""Commission fold162_selfcheck.py: plant defects, require RED on every one.

An uncommissioned green is not evidence. Each plant is anchored on a unique
full-line-or-longer literal and HARD-ERRORS if the anchor does not land, so a
plant that silently failed to apply cannot be scored as a pass.

Never mutates the real script: every arm runs against a copy in TEMP.
"""
import io
import os
import subprocess
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

REAL = "experiments/ORCH-drift-check/fold162.py"
CHECK = "experiments/ORCH-drift-check/fold162_selfcheck.py"

src = open(REAL, encoding="utf-8").read()

# (name, anchor that must exist exactly once, replacement)
PLANTS = [
    ("D1 digit in a fact number",
     "a recursive search found **33 matches across 9 files**",
     "a recursive search found **34 matches across 9 files**"),
    ("D2 word swapped in a discipline",
     "**A default is a decision, and an unset `env::var` is a decision nobody wrote down.**",
     "**A default is a decision, and an unset `env::var` is a decision somebody wrote down.**"),
    ("D3 whole fact row deleted",
     "| 1741 | MEASURED | ORCH |",
     "| 1741 | MEASURED | XXXX |"),
    ("D4 citation path altered",
     "`optics.rs:476` and `merge.rs:525`",
     "`optics.rs:476` and `merge.rs:526`"),
    ("D5 the amended sentence reverted to its wrong original",
     "`outlier.rs` is **still not reachable from the render path**",
     "`outlier.rs` is **still** orphaned and nothing refers to it"),
]


def run(path):
    r = subprocess.run([sys.executable, CHECK, path],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


rc, out = run(REAL)
print(f"BASELINE (unmutated): rc={rc}  {out.splitlines()[-1] if out else ''}")
if rc != 0:
    print("FAIL: baseline is not green; commissioning is meaningless.")
    sys.exit(1)

tmpdir = tempfile.mkdtemp(prefix="fold162-commission-")
caught = 0
for name, anchor, repl in PLANTS:
    n = src.count(anchor)
    if n != 1:
        print(f"PLANT ANCHOR NOT UNIQUE for {name}: {n} occurrence(s) -- ABORT")
        sys.exit(2)
    mutated = src.replace(anchor, repl, 1)
    if mutated == src:
        print(f"MUTATION DID NOT APPLY for {name} -- ABORT")
        sys.exit(2)
    p = os.path.join(tmpdir, f"mut_{caught}.py")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(mutated)
    rc, out = run(p)
    verdict = "CAUGHT (red)" if rc != 0 else "MISSED (green)"
    if rc != 0:
        caught += 1
    print(f"  {name}: {verdict}")

print()
print(f"COMMISSIONED {caught}/{len(PLANTS)} planted defects caught.")
sys.exit(0 if caught == len(PLANTS) else 1)
