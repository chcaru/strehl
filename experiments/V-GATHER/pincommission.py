r"""Commission the pin guard. A guard that has never refused anything is not a guard.

Twenty arms. Each names the verdict BEFORE the number is read, and each checks
the REASON as well as the exit code -- a refusal for the wrong reason is a pass
by luck, and this project has already been bitten by a green that came from a
check never executing.

ARMS 13-14 PERTURB THE SEALS, NOT THE BINARY. Every instrument convicted in this
lane tonight passed an otherwise exemplary commissioning while sharing one
un-perturbed reference across all its arms. The same blindness here would be a
guard with the pin table baked in: it would pass arms 1-12 and still be a
hand-written list wearing a scanner's clothes. So re-seal a synthetic corpus with
the hash of the UNSEALED binary and require the verdicts to swap.

ARMS 15-18 ARE POSITIVE CONTROLS ON AN ABSENCE, and they exist because this lane
reported a build "NOT FOUND" that was present the whole time. The scan missed it
twice over: by NAME, and then, while that was being corrected, by SHAPE.

    "Not found" is a statement about the query until the query's reach is
    measured.

RETRACTED IN PLACE -- and this is the same error in my own hands, again. I told
the orchestrator the SHAPE defect was directory reparse points, because 1,317 of
them sit under C:\dev and glob is known not to descend some of them. I never
measured it. reachwhy.py classifies every path os.walk returns and glob does not,
and the cause is not reparse points at all: glob's * and ** never match a path
component beginning with a dot, so .cargo-target-defect\... is invisible to it.

    dot-prefixed component in path : 127
    under a directory reparse point:   0
    neither                        :   0
    sum                            : 127   (= the entire miss set)

A decoy behind a junction is therefore NOT a control -- glob descends it. Arm
REACH-junction is kept to record that the hypothesis was tested and died. Had I
built this suite on the mechanism I asserted, all four decoys would have been
found by both queries, every arm would have passed, and the suite would have been
incapable of failing.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pinmanifest import find_binaries

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "pincheck.py")
SCRATCH = r"C:\dev\strehl-out\V-GATHER\pincommission\acceptance"
REACH = r"C:\dev\strehl-out\V-GATHER\pincommission\reach"

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


def plant_decoys():
    r"""Four decoys, one per hypothesis about how a scan misses a file that exists.

    plain      -- both queries find it. Proves the scan works; trivial by design.
    oddname    -- strehl-pinned.exe. The exact-name query cannot see it. This is
                  the miss that actually happened: 066A87AB was reported NOT
                  FOUND while sitting at V-REVIEW\bin\strehl-pinned.exe.
    dot-hidden -- under a component starting with a dot. glob's ** cannot see it.
                  Measured cause of all 127 real misses under C:\dev.
    junction   -- behind a directory reparse point. A REFUTED hypothesis, kept
                  visible: glob descends it, so it is not a defect and not a
                  control. Returns in the found set but is not claimed as hard.
    """
    real = os.path.join(REACH, "real")
    hidden = os.path.join(REACH, "hidden")
    dot = os.path.join(real, ".cargo-target-decoy", "release")
    for d in (os.path.join(real, "a"), os.path.join(real, "b"), hidden, dot):
        os.makedirs(d, exist_ok=True)
    made = {
        "plain": os.path.join(real, "a", "strehl.exe"),
        "oddname": os.path.join(real, "b", "strehl-pinned.exe"),
        "dot-hidden": os.path.join(dot, "strehl.exe"),
        "junction": os.path.join(hidden, "strehl-alt.exe"),
    }
    for i, p in enumerate(made.values()):
        with open(p, "wb") as fh:
            fh.write(b"decoy-%d" % i)
    link = os.path.join(real, "viajunction")
    if not os.path.exists(link):
        subprocess.run(["cmd", "/c", "mklink", "/J", link, hidden],
                       capture_output=True, text=True)
    made["junction"] = os.path.join(link, "strehl-alt.exe")
    return real, made, {"oddname", "dot-hidden"}


if __name__ == "__main__":
    os.makedirs(SCRATCH, exist_ok=True)
    seal("SHIP-V2", [H_V4] * 3)
    seal("MIXED", [H_V4, H_STRAY])
    os.makedirs(os.path.join(SCRATCH, "EMPTY"), exist_ok=True)
    seal("RESEALED", [H_V4] * 3)

    arms = [
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

    print("\nDENOMINATOR PERTURBATION -- re-seal RESEALED with the STRAY's hash.")
    print("Nothing about either binary changes. Only the reference moves.")
    for f in os.listdir(os.path.join(SCRATCH, "RESEALED")):
        os.remove(os.path.join(SCRATCH, "RESEALED", f))
    seal("RESEALED", [H_STRAY] * 3)
    for label, exe, want, text in (
            ("RED    previously-matching binary, after re-seal", V4, 2, "does not match"),
            ("GREEN  previously-refused stray, after re-seal", STRAY, 0, "MATCH")):
        rc, out = run(exe, "RESEALED", SCRATCH)
        good = rc == want and text.lower() in out.lower()
        ok = ok and good
        print("%-52s %6d %6d  %s" % (label, want, rc, "ok" if good else "WRONG"))

    print("\nREACH -- planted decoys the scan is REQUIRED to return.")
    root, decoys, hard = plant_decoys()
    import glob as _g
    found = {os.path.normcase(os.path.realpath(p)) for p in find_binaries(root)}
    narrow = {os.path.normcase(os.path.realpath(p))
              for p in find_binaries(root, "strehl.exe")}
    globbed = {os.path.normcase(os.path.realpath(p))
               for p in _g.glob(os.path.join(root, "**", "strehl*.exe"), recursive=True)}
    print("%-52s %8s %8s  %s" % ("decoy", "found", "old qry", "verdict"))
    for label, p in decoys.items():
        rp = os.path.normcase(os.path.realpath(p))
        hit = rp in found
        oldq = rp in (narrow if label == "oddname" else globbed)
        # A control is only a control if the broken query provably misses it.
        trivial = (label in hard) and oldq
        good = hit and not trivial
        ok = ok and good
        print("%-52s %8s %8s  %s"
              % ("REACH  " + label, "yes" if hit else "NO",
                 "yes" if oldq else "missed",
                 "ok" if good else ("WRONG -- not found" if not hit
                                    else "WRONG -- control is trivial")))
    print("  scan returned %d under the decoy root; exact-name %d; glob ** %d."
          % (len(found), len(narrow), len(globbed)))
    print("  junction is a refuted hypothesis, not a control: glob descends it.")

    n = len(arms) + 2 + len(decoys)
    print("\n%s" % ("COMMISSIONED: %d/%d arms landed on their intended side -- "
                    "including both directions of a seal perturbation and four "
                    "planted decoys, two of which the old query provably misses."
                    % (n, n) if ok else
                    "NOT COMMISSIONED: an arm landed on the wrong side."))
    sys.exit(0 if ok else 1)
