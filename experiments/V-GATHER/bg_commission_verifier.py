r"""Commission bg_verify.py against CONCLUSION-FLIPPING mutations.

ORCH's finding: a presence test cannot detect a reversed conclusion. This does
not reason about that -- it flips the conclusions and reads the exit code.

Every mutation is anchored on a string that must occur EXACTLY ONCE, and the
harness hard-errors if the anchor does not land, so a mutation that silently
failed to apply cannot be scored as "the verifier caught nothing wrong".
The document is restored from a $TEMP copy, never via git checkout.
"""
import io, os, shutil, subprocess, sys, tempfile

DOC = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-GATHER.md"
VER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bg_verify.py")
BAK = os.path.join(tempfile.gettempdir(), "V-GATHER.md.commission-backup")

MUTATIONS = [
 ("M1 flip the headline verdict",        "CONCLUSION",
  "**The first condition fired. Rim is unmoved**",
  "**No condition fired. Rim moved materially**"),
 ("M2 flip the mechanism conclusion",    "CONCLUSION",
  "So **rim is not a coarse-scale selection artifact",
  "So **rim IS a coarse-scale selection artifact"),
 ("M3 flip the third-condition finding", "CONCLUSION",
  "The third condition - the trap - **does not arise**",
  "The third condition - the trap - **fired**"),
 ("M4 turn the REFUSED subject into a number", "VERDICT TOKEN",
  "| coffee-bubbles | 3.1 -> 60.6% | *REFUSED*",
  "| coffee-bubbles | 3.1 -> 60.6% | -0.412%"),
 ("M5 delete my own self-correction",    "VERDICT TOKEN",
  "My \u00a715.3 is corrected",
  "My section 15.3 stands as written"),
 ("M6 perturb the dose column (positive control)", "NUMBER",
  "| bee-2-cpl | 0.0 -> 33.3% |", "| bee-2-cpl | 0.0 -> 93.3% |"),
 ("M7 duplicate the verdict sentence elsewhere", "DUPLICATE",
  "### 16.10", "**The first condition fired. Rim is unmoved**\n\n### 16.10"),
 ("M8 flip the split table without touching prose", "NUMBER",
  "| 119MSDCF | **0.9262** | 1.0013 |", "| 119MSDCF | **0.8262** | 1.0013 |"),
]

orig = io.open(DOC, encoding="utf-8", newline="").read()
shutil.copyfile(DOC, BAK)
print("backup: %s (%d bytes)\n" % (BAK, os.path.getsize(BAK)))

def run_verifier():
    r = subprocess.run([sys.executable, VER], capture_output=True, text=True)
    failed = [ln.split()[0] for ln in r.stdout.splitlines() if "**FAIL**" in ln]
    extra = [ln.strip()[:44] for ln in r.stdout.splitlines()
             if "UNDECLARED SKIP" in ln or "DID NOT OCCUR" in ln]
    return r.returncode, (failed + extra)

base, _ = run_verifier()
print("unmutated document -> exit %d (%s)\n" % (base, "GREEN" if base == 0 else "RED"))
if base != 0:
    print("ABORT: verifier is not green before mutation; nothing can be learned.")
    raise SystemExit(2)

print("%-46s %-14s %-16s %s" % ("mutation", "class", "verifier", "tripped"))
print("-" * 104)
missed = []
try:
    for name, cls, old, new in MUTATIONS:
        n = orig.count(old)
        if n != 1:
            raise SystemExit("ANCHOR NOT UNIQUE for %s: found %d occurrences" % (name, n))
        io.open(DOC, "w", encoding="utf-8", newline="").write(orig.replace(old, new, 1))
        rc, which = run_verifier()
        verdict = "RED  caught" if rc != 0 else "GREEN **MISSED**"
        if rc == 0: missed.append((name, cls))
        print("%-46s %-14s %-16s %s" % (name, cls, verdict, ",".join(which) or "-"))
        io.open(DOC, "w", encoding="utf-8", newline="").write(orig)
finally:
    shutil.copyfile(BAK, DOC)
    after = io.open(DOC, encoding="utf-8", newline="").read()
    print("\nrestored from backup, byte-identical to original: %s" % (after == orig))

print("\n%d of %d mutations MISSED" % (len(missed), len(MUTATIONS)))
for nm, cls in missed:
    print("   MISSED  [%s]  %s" % (cls, nm))