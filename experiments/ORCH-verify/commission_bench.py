"""Commission vbench.py by planting the exact defects it claims to catch.

vbench.py asserts that the owner-facing bench sheet is lane M166's capture
protocol verbatim. A verifier that has never failed is indistinguishable from
one that cannot fail, and this one is guarding a claim I make about my own
fidelity -- so it is precisely the check most worth proving.

Three plants, one per failure mode the verifier claims to detect, plus one
inert edit that must NOT trip it. The inert arm is the one that separates a
real check from a check that merely reacts to any edit at all.

The live tree is never written: docs/ is copied into TEMP and every mutation is
applied there. vbench.py takes a repo root as argv[1], which is what makes that
possible.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "experiments" / "ORCH-verify" / "vbench.py"
SCRATCH = Path(tempfile.gettempdir()) / "orch-bench-scratch"

OWNER = "docs/OWNER-ACTIONS.md"

# (label, file, unique anchor, replacement, regex the output must then contain)
# Each anchor is a full distinctive string, and apply() hard-errors unless it
# matches exactly once -- a plant that silently fails to land would otherwise
# read as a passing control.
MUTATIONS = [
    # A single altered word inside a step. This is the realistic drift: a
    # copy-edit that changes what the owner is instructed to do.
    ("step text drift", OWNER,
     "move axially to the accepted `1.32x` placement",
     "move axially to the accepted `1.31x` placement",
     r"RED\s+step 6\s+DIVERGED"),
    # A wrong frame count. Must be caught twice: on the block and on the sum.
    # Note the sum message: a block whose count fails is *excluded* from the
    # total rather than counted wrongly, so the sum drops by the whole block
    # (1092 - 164 = 928) instead of rising to 1093. That is fail-closed and
    # correct; the expectation below was wrong on first run and is fixed here.
    ("frame count drift", OWNER,
     "**Dominance witness — 164 more frames.**",
     "**Dominance witness — 165 more frames.**",
     r"RED\s+step 7\s+frame count is 165, expected 164"),
    ("frame sum drift", OWNER,
     "**Dominance witness — 164 more frames.**",
     "**Dominance witness — 165 more frames.**",
     r"RED\s+blocks sum to 928, not the 1092"),
    # A step that loses its number, which is how an item silently merges into
    # its predecessor and disappears without leaving a gap.
    ("step disappears", OWNER,
     "> 9. **Physical controls",
     "> **Physical controls",
     r"RED\s+step 9\s+missing from the owner bench sheet"),
]

# Must NOT trip the verifier: prose of mine that sits outside the sheet.
INERT = (OWNER, "This is that bench sheet.", "This is the bench sheet.")


def apply(text, anchor, replacement):
    hits = text.count(anchor)
    if hits != 1:
        raise SystemExit("MUTATION ANCHOR MATCHED %d TIMES (need exactly 1): %r"
                         % (hits, anchor))
    return text.replace(anchor, replacement)


def build():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH, ignore_errors=True)
    shutil.copytree(ROOT / "docs", SCRATCH / "docs")


def run():
    p = subprocess.run([sys.executable, str(VERIFIER), str(SCRATCH)],
                       capture_output=True, text=True)
    return p.stdout + p.stderr


build()
base = run()
print("baseline     : %s" % ("GREEN" if "VERDICT: GREEN" in base else "RED"))
if "VERDICT: GREEN" not in base:
    print(base)
    raise SystemExit("scratch baseline is not GREEN; controls would be meaningless")

caught = missed = 0
for label, rel, anchor, repl, expect in MUTATIONS:
    target = SCRATCH / rel
    pristine = target.read_text(encoding="utf-8")
    target.write_text(apply(pristine, anchor, repl), encoding="utf-8",
                      newline="")
    out = run()
    ok = re.search(expect, out) is not None and "VERDICT: RED" in out
    print("  %-18s %s" % (label, "control PASSED" if ok else "CONTROL MISSED"))
    if not ok:
        print("    expected /%s/ and VERDICT: RED" % expect)
        print("    got:\n%s" % out)
        missed += 1
    else:
        caught += 1
    target.write_text(pristine, encoding="utf-8", newline="")

rel, anchor, repl = INERT
target = SCRATCH / rel
pristine = target.read_text(encoding="utf-8")
target.write_text(apply(pristine, anchor, repl), encoding="utf-8", newline="")
out = run()
inert_ok = "VERDICT: GREEN" in out
print("  %-18s %s" % ("inert edit",
                      "survived (correct)" if inert_ok else "TRIPPED (wrong)"))
target.write_text(pristine, encoding="utf-8", newline="")

final = run()
print("final run    : %s" % ("GREEN" if "VERDICT: GREEN" in final else "RED"))

print("\ncontrols     : %d caught + %d missed = %d of %d"
      % (caught, missed, caught, len(MUTATIONS)))
print("inert control: %s" % ("1 of 1 survived" if inert_ok else "0 of 1"))
good = missed == 0 and inert_ok and "VERDICT: GREEN" in final
print("\nVERDICT: %s" % ("COMMISSIONED" if good else "NOT COMMISSIONED"))
raise SystemExit(0 if good else 1)
