"""Commission the vr_lib pin guard in BOTH directions.

GREEN arms must derive the right pin. RED arms must raise. The trap arm
reproduces the exact one-line edit that was dangerous before the fix.
"""
import os, sys, shutil
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW")
import vr_lib as V

SCRATCH = r"C:\dev\strehl-out\V-REVIEW\pinguard"
ACC = r"C:\dev\strehl-out\acceptance"
rows = []


def green(name, ship, arm, want_pin):
    try:
        seal, n = V.corpus_seal(ship, arm)
        exe, pin = V.pin_for(seal)
        ok = (pin == want_pin)
        rows.append((name, "PASS" if ok else "WRONG-PIN",
                     "%s -> pin %s (%d masters sealed)" % (arm, pin, n)))
    except Exception as e:
        rows.append((name, "UNEXPECTED-RAISE", str(e).splitlines()[0]))


def red(name, ship, arm, expect):
    try:
        seal, n = V.corpus_seal(ship, arm)
        exe, pin = V.pin_for(seal)
        rows.append((name, "FAILED-TO-REFUSE", "returned pin %s" % pin))
    except RuntimeError as e:
        msg = " ".join(str(e).split())
        rows.append((name, "RED ok" if expect in str(e) else "RED wrong-reason",
                     msg[:150]))


def mkcorpus(sub, seals, arm):
    d = os.path.join(SCRATCH, sub)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    for i, s in enumerate(seals):
        with open(os.path.join(d, "subj%d--%s.tiff.ok" % (i, arm)), "w") as f:
            f.write(s)
    return d


print("== GREEN: the pin must be DERIVED from each corpus's own seal ==")
green("G1 SHIP-V3", os.path.join(ACC, "SHIP-V3"), "SHIP-V3", "740e7056")
green("G2 SHIP-V4", os.path.join(ACC, "SHIP-V4"), "SHIP-V4", "9b05d0b7")

print("== RED: every way of being cross-gauge must raise ==")
red("R1 seal matches no pin",
    mkcorpus("nopin", ["A" * 64], "X"), "X", "no pin matches")
red("R2 corpus not internally sealed",
    mkcorpus("split", [V.CORPUS_SEAL, "B" * 64], "X"), "X", "not internally sealed")
red("R3 unsealed corpus",
    mkcorpus("empty", [], "X"), "X", "no .ok seals")

for n, verdict, detail in rows:
    print("  %-28s %-18s %s" % (n, verdict, detail))

print()
print("== TRAP ARM: the exact one-line edit that was dangerous before ==")
seal4, _ = V.corpus_seal(os.path.join(ACC, "SHIP-V4"), "SHIP-V4")
old_exe = r"C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe"
old_hash = V._sha256(old_exe)
new_exe, new_pin = V.pin_for(seal4)
print("  SHIP-V4 seal                    %s" % seal4)
print("  OLD hard-coded EXE hashed       %s" % old_hash)
print("  OLD would have been cross-gauge %s" % (old_hash != seal4))
print("  NEW derived pin                 %s  hash %s" % (new_pin, V._sha256(new_exe)))
print("  NEW matches seal                %s" % (V._sha256(new_exe) == seal4))
