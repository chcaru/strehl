"""Commission the pin guard. A guard that has never refused anything is not a guard.

Twelve arms. Each names the verdict BEFORE the number is read, and each checks
the REASON as well as the exit code -- a refusal for the wrong reason is a pass
by luck, and this project has already been bitten by a green that came from a
check never executing.

THE ARM THAT MATTERS MOST IS 11-12: THEY PERTURB THE SEALS, NOT THE BINARY.
Every instrument convicted in this lane tonight passed an otherwise exemplary
commissioning while sharing one un-perturbed reference across all its arms.
orch_sharp1to1's three arms all drew from a single source set, so none of them
could see that its denominator was on another gauge. The same shape of blindness
here would be a guard with the pin table baked in: it would pass arms 1-10 and
still be a hand-written list wearing a scanner's clothes.

So: re-seal a synthetic corpus with the hash of the UNSEALED binary, and require
the verdicts to swap. The previously-good binary must now be REFUSED and the
previously-refused binary must now PASS. Only a manifest genuinely derived from
the seals can do that.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "pincheck.py")
SCRATCH = r"C:\dev\strehl-out\V-GATHER\pincommission\acceptance"

V4 = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
V3 = r"C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe"
STRAY = r"C:\dev\strehl-out\PIN-V3\strehl.exe"
GHOST = r"C:\dev\strehl-out\PIN-V3\does-not-exist.exe"

H_V4 = "44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490"
H_STRAY = "B50EABC12D16B29095AAE82240698F3D51BFB64482D4993725437B4CE11A7C99"


def seal(corpus, values):
    d = os.path.join(SCRATCH, corpus)
    os.makedirs(d, exist_ok=True)
    for i, v in enumerate(values):
        with open(os.path.join(d, "s%02d--%s.tiff.ok" % (i, corpus)), "w",
                  encoding="utf-8") as f:
            f.write(v + "\n")
    return d


def run(exe, corpus, acc=None):
    cmd = [sys.executable, CHECK, "--exe", exe, "--corpus", corpus]
    if acc:
        cmd += ["--acceptance", acc]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


if __name__ == "__main__":
    os.makedirs(SCRATCH, exist_ok=True)
    seal("SHIP-V2", [H_V4] * 3)              # genuinely matching, but barred
    seal("MIXED", [H_V4, H_STRAY])           # disagreeing provenance
    d = os.path.join(SCRATCH, "EMPTY")
    os.makedirs(d, exist_ok=True)            # exists, attests nothing
    seal("RESEALED", [H_V4] * 3)             # arm 11 baseline; re-sealed for 12

    arms = [
        # exe,   corpus,     acc,      want_exit, want_text
        ("GREEN  9b05d0b7 vs the corpus it sealed", V4, "SHIP-V4", None, 0, "MATCH"),
        ("GREEN  740e7056 vs the corpus it sealed", V3, "SHIP-V3", None, 0, "MATCH"),
        ("RED    the stray named PIN-V3 vs SHIP-V3", STRAY, "SHIP-V3", None, 2, "sealed by NO corpus"),
        ("RED    the stray named PIN-V3 vs SHIP-V4", STRAY, "SHIP-V4", None, 2, "sealed by NO corpus"),
        ("RED    right build, wrong corpus (V3 pin vs V4)", V3, "SHIP-V4", None, 2, "wrong corpus"),
        ("RED    right build, wrong corpus (V4 pin vs V3)", V4, "SHIP-V3", None, 2, "wrong corpus"),
        ("RED    binary does not exist", GHOST, "SHIP-V4", None, 3, "no such binary"),
        ("RED    corpus does not exist", V4, "SHIP-V9", None, 3, "no such corpus"),
        ("RED    barred corpus, binary genuinely matches", V4, "SHIP-V2", SCRATCH, 2, "barred from scoring"),
        ("RED    corpus of mixed provenance", V4, "MIXED", SCRATCH, 2, "seals DISAGREE"),
        ("RED    corpus carries no seals", V4, "EMPTY", SCRATCH, 2, "carries no .ok seals"),
        ("GREEN  seals perturbed: matching binary, before", V4, "RESEALED", SCRATCH, 0, "MATCH"),
    ]

    print("%-52s %6s %6s  %s" % ("arm", "want", "got", "verdict"))
    print("-" * 96)
    ok = True
    for label, exe, corpus, acc, want, text in arms:
        rc, out = run(exe, corpus, acc)
        good = rc == want and text.lower() in out.lower()
        ok = ok and good
        print("%-52s %6d %6d  %s" % (label, want, rc, "ok" if good else "WRONG"))
        if not good:
            print("      wanted text %r in output" % text)

    # ---- THE DENOMINATOR ARM -------------------------------------------------
    print("\nDENOMINATOR PERTURBATION -- re-seal RESEALED with the STRAY's hash.")
    print("Nothing about either binary changes. Only the reference moves.")
    for f in os.listdir(os.path.join(SCRATCH, "RESEALED")):
        os.remove(os.path.join(SCRATCH, "RESEALED", f))
    seal("RESEALED", [H_STRAY] * 3)
    swap = [
        ("RED    previously-matching binary, after re-seal", V4, 2, "does not match"),
        ("GREEN  previously-refused stray, after re-seal", STRAY, 0, "MATCH"),
    ]
    for label, exe, want, text in swap:
        rc, out = run(exe, "RESEALED", SCRATCH)
        good = rc == want and text.lower() in out.lower()
        ok = ok and good
        print("%-52s %6d %6d  %s" % (label, want, rc, "ok" if good else "WRONG"))

    print("\n%s" % ("COMMISSIONED: 14/14 arms landed on their intended side, "
                    "including both directions of a seal perturbation. The "
                    "verdict follows the seals, so the manifest is derived."
                    if ok else
                    "NOT COMMISSIONED: an arm landed on the wrong side."))
    sys.exit(0 if ok else 1)
