"""Commission the Ask 2c / M4 pins in v2954.py.

These guard OWNER-FACING text that changes what the owner physically shoots, so
a silent no-op here is more expensive than usual: it would let the guidance drift
back to "reshoot at a different exposure", which M152 proved cannot work, or let
the "this does not pass M4" caveat disappear once the sittings exist.

Every arm mutates the real OWNER-ACTIONS.md, re-runs v2954.py as a subprocess,
and requires the named check to XFAIL. The file is backed up to %TEMP% and
restored in a finally block. `git checkout --` is never used: it reverts to HEAD
and would discard other agents' uncommitted work in this shared tree.

Mutations are anchored on unique strings and HARD-ERROR if the anchor does not
land, because a mutation that silently fails to apply yields a green that means
nothing. One INERT arm changes prose no check reads and requires GREEN, so that
"the suite fails on any edit" cannot masquerade as "every check is wired".
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNER = ROOT / "docs" / "OWNER-ACTIONS.md"
VERIF = HERE / "v2954.py"
BACKUP = Path(tempfile.gettempdir()) / "commission_m4ask_owner_backup.md"


def run():
    r = subprocess.run([sys.executable, str(VERIF)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def mutate(anchor, repl):
    text = OWNER.read_text(encoding="utf-8")
    n = text.count(anchor)
    if n != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND: %r matched %d times (need 1)"
                         % (anchor[:70], n))
    OWNER.write_text(text.replace(anchor, repl), encoding="utf-8")


# (label that must XFAIL, anchor, replacement, defect simulated)
ARMS = [
    ("m4 sittings buy no axis",
     "full M4 remains blocked `(a)`, `(b)`\nand `(d)`",
     "full M4 is close to scoreable",
     "the blocker list is softened into optimism"),
    ("m4 axis caveat intact",
     "They do not buy\nan axis.",
     "They may well buy the axis.",
     "the caveat is reversed once the sittings exist"),
    ("m4 frames add no sites",
     "can only *remove* survivors, never add one",
     "can usually add a few more survivors",
     "the deficit drifts back to a frame-count reading"),
    ("m4 flatness not exposure",
     "**So no exposure change rescues it.**",
     "**So a longer exposure should rescue it.**",
     "the owner is sent to reshoot the same target at a new exposure"),
    ("m4 foam plausibility only",
     "**that is plausibility, not sufficiency.**",
     "**that is sufficient.**",
     "M152's hedge is upgraded into a guarantee"),
    ("m4 error stays attributed",
     "**That\nwas wrong, and M152 said so plainly rather than letting me keep it.**",
     "**This has now been refined.**",
     "my own error is tidied off the record"),
    # Cross-document arm: break ONLY the owner copy. A check that reads just one
    # side, or that re-reads the same file twice, would pass this.
    ("m4 coffee band best",
     "a best-case ratio of `1.091006`",
     "a best-case ratio of `1.091007`",
     "the owner copy drifts one digit from M152's committed source"),
]

INERT = ("bubble field", "field of bubbles", "prose no check reads is reworded")


def main():
    caught = missed = inert_ok = 0
    notes = []
    shutil.copyfile(OWNER, BACKUP)
    try:
        base = run()
        if "VERDICT: GREEN" not in base:
            raise SystemExit("BASELINE NOT GREEN -- fix that first:\n" + base[-1200:])
        print("baseline: GREEN\n")

        for label, anchor, repl, why in ARMS:
            mutate(anchor, repl)
            try:
                out = run()
            finally:
                shutil.copyfile(BACKUP, OWNER)
            if ("XFAIL %s" % label) in out:
                caught += 1
                print("CAUGHT   %-26s %s" % (label, why))
            else:
                missed += 1
                notes.append(label)
                print("MISSED   %-26s %s  <-- NO-OP" % (label, why))

        mutate(INERT[0], INERT[1])
        try:
            out = run()
        finally:
            shutil.copyfile(BACKUP, OWNER)
        if "VERDICT: GREEN" in out:
            inert_ok = 1
            print("INERT-OK %-26s %s" % ("(unread prose)", INERT[2]))
        else:
            missed += 1
            notes.append("INERT")
            print("INERT-BAD suite fails on unrelated prose")
    finally:
        shutil.copyfile(BACKUP, OWNER)
        if BACKUP.exists():
            os.remove(BACKUP)

    final = run()
    restored = "VERDICT: GREEN" in final
    print("\nrestored owner doc, verifier re-run: %s"
          % ("GREEN" if restored else "NOT GREEN -- RESTORE FAILED"))
    total = len(ARMS) + 1
    print("\ncaught            : %d of %d" % (caught, len(ARMS)))
    print("inert green       : %d of 1" % inert_ok)
    print("missed            : %d" % missed)
    print("accounted         : %d of %d arms" % (caught + missed + inert_ok, total))
    ok = missed == 0 and inert_ok == 1 and restored
    print("\n%s" % ("COMMISSIONED" if ok else "NOT COMMISSIONED: %s" % notes))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
