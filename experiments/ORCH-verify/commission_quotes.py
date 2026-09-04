"""Commission the STATUS 2.9.66 cross-document quote checks.

These four checks read files that *other lanes own and are actively editing*.
Mutating them in the live tree would race a lane's commit and could corrupt its
work, so this harness builds a scratch repo root in TEMP, confirms the verifier
is GREEN against it, and plants each defect there instead. The live tree is
never written.

v2954.py takes a repo root as argv[1], which is what makes this possible.
"""
import shutil
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "experiments" / "ORCH-verify" / "v2954.py"
SCRATCH = Path(tempfile.gettempdir()) / "orch-xdoc-scratch"

# The verifier builds most experiment paths by concatenation (`E + "..."`), so
# scraping string literals misses them and a missing source reads as RED --
# indistinguishable from a real failure. Instead docs/ is copied for real and
# experiments/ is junctioned read-only. Every mutation below targets docs/, so
# nothing under experiments/ is ever written.

# (check label that must flip to XFAIL, file, unique anchor, replacement)
MUTATIONS = [
    # Invert the licence 2.9.66 rests on: if correctness arms may NOT run under
    # load, overruling M139's host lock was wrong.
    ("m12 load rule", "docs/research/M160-amendment6-reachability.md",
     "Correctness arms may run under load",
     "Correctness arms may not run under load"),
    # Remove the diagnosed cause: the fix-first ordering loses its basis.
    ("m12 root cause", "docs/research/M160-amendment6-reachability.md",
     "because reduction order changes with worker count",
     "because output ordering changes with thread affinity"),
    # Withdraw achievability: fix-then-measure becomes measure-a-known-failure.
    ("m12 fix achievable", "docs/research/M166-bar-achievability.md",
     "can make all five outputs byte-identical",
     "cannot make all five outputs byte-identical"),
    # Clear the failing diagnostic: M12 would no longer need a fix at all.
    ("m12s diagnostic fail", "docs/STATUS.md",
     "**M12-S, cross-worker scaling invariance** -- diagnostic FAIL.",
     "**M12-S, cross-worker scaling invariance** -- diagnostic PASS."),
    ("m166 target holds",
     "docs/research/M166-reference-information-dominance-physical.md",
     "TARGET HOLDS AT 1.32x", "TARGET MOVES TO 1.18x"),
    ("m166 rehearsal first",
     "docs/research/M166-reference-information-dominance-physical.md",
     "only a pass licenses the `1,147`-frame holdout sitting.",
     "the holdout sitting needs no rehearsal."),
    ("m166 weakest cell",
     "docs/research/M166-reference-information-dominance-physical.md",
     "1.03405", "1.44405"),
    ("m164 shared objective", "docs/research/M164-reference-dominance.md",
     "SHARED OBJECTIVE SUFFICIENT", "SHARED OBJECTIVE INSUFFICIENT"),
    # The inequality my own briefing got wrong. If the spec ever reads
    # otherwise, STATUS 2.9.67's account of my error becomes false.
    ("m164 strictly positive",
     "docs/research/M164-reference-identifiability.md",
     "must be strictly positive", "must exceed unity"),
    # The inequality my own briefing got wrong. If the spec ever reads
    # otherwise, STATUS 2.9.67's account of my error becomes false.
    ("m169 commission sha", "docs/research/M169-m3-veil.md",
     "3d69bbcd", "4e70ccde"),
    ("m169 green recovery arm", "docs/research/M169-m3-veil.md",
     "0.005649", "0.009999"),
    ("m169 axis has no CI", "docs/research/M169-m3-veil.md",
     "confidence_interval=NO CI", "confidence_interval=[0.1, 0.9]"),
]


def build_scratch():
    if SCRATCH.exists():
        # Remove the junction before the tree, or rmtree would follow it into
        # the live experiments/ directory and delete real lane work.
        link = SCRATCH / "experiments"
        if link.exists():
            subprocess.run(["cmd", "/c", "rmdir", str(link)],
                           capture_output=True)
        shutil.rmtree(SCRATCH, ignore_errors=True)
    shutil.copytree(ROOT / "docs", SCRATCH / "docs")
    r = subprocess.run(["cmd", "/c", "mklink", "/J",
                        str(SCRATCH / "experiments"),
                        str(ROOT / "experiments")], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("could not junction experiments/: " + r.stdout + r.stderr)


def teardown():
    link = SCRATCH / "experiments"
    if link.exists():
        subprocess.run(["cmd", "/c", "rmdir", str(link)], capture_output=True)
    shutil.rmtree(SCRATCH, ignore_errors=True)


def run():
    r = subprocess.run([sys.executable, "-B", str(VERIFIER), str(SCRATCH)],
                       capture_output=True, text=True, cwd=str(ROOT))
    return r.returncode, r.stdout + r.stderr


VOWNER = ROOT / "experiments" / "ORCH-verify" / "vowner0906.py"

# Mutations checked against vowner0906.py rather than v2954.py. The banner tells
# the owner to shoot on the strength of six verbatim lane quotes; each must be
# shown to fail when its source no longer says what the banner claims.
OWNER_MUTATIONS = [
    ("banner m166 target holds",
     "docs/research/M166-reference-information-dominance-physical.md",
     "TARGET HOLDS AT 1.32x", "TARGET MOVES TO 1.20x"),
    ("banner m166 cannot admit rig",
     "docs/research/M166-reference-information-dominance-physical.md",
     "Diffraction arithmetic cannot admit the rig.",
     "Diffraction arithmetic is sufficient to admit the rig."),
    ("banner m164 shared objective",
     "docs/research/M164-reference-dominance.md",
     "SHARED OBJECTIVE SUFFICIENT", "SHARED OBJECTIVE INSUFFICIENT"),
    ("banner m166 rehearsal first",
     "docs/research/M166-reference-information-dominance-physical.md",
     "only a pass licenses the `1,147`-frame holdout sitting.",
     "the holdout sitting may proceed regardless."),
    # Drift the owner-facing total away from the lane's figure.
    ("revsn  owner states the revised total in context", "docs/OWNER-ACTIONS.md",
     "`891` to `1,147` registered frames", "`891` to `1,203` registered frames"),
    ("revsn  owner attributes the +256 to its components", "docs/OWNER-ACTIONS.md",
     "three reference strips become four (`+32`)",
     "three reference strips become five (`+64`)"),
]


def run_owner():
    r = subprocess.run([sys.executable, "-B", str(VOWNER), str(SCRATCH)],
                       capture_output=True, text=True, cwd=str(ROOT))
    return r.returncode, r.stdout + r.stderr


def apply_mutation(text, anchor, replacement):
    """Replace a quotation that may be wrapped across lines in the source.

    Markdown reflows prose, so a quoted sentence rarely exists as one literal
    line, and inside a blockquote a wrap inserts "\\n> " mid-sentence. Joining
    the anchor's tokens on [\\s>]+ makes the mutation land in either case.
    Requires exactly one match: a missing anchor is a broken control, and
    multiple matches make the control ambiguous.
    """
    pattern = r"[\s>]+".join(re.escape(tok) for tok in anchor.split())
    hits = list(re.finditer(pattern, text))
    if len(hits) != 1:
        raise SystemExit("MUTATION ANCHOR MATCHED %d TIMES (need exactly 1): %r"
                         % (len(hits), anchor))
    return text[:hits[0].start()] + replacement + text[hits[0].end():]


def main() -> int:
    for _lbl, _rel, _a, _r in MUTATIONS:
        if not _rel.startswith("docs/"):
            raise SystemExit("REFUSING: mutation targets %s, which is outside "
                             "the copied docs/ tree and would write through "
                             "the read-only junction" % _rel)
    build_scratch()
    print("scratch root : %s" % SCRATCH)
    print("live tree    : docs/ copied, experiments/ junctioned read-only")

    rc, out = run()
    if rc != 0 or "VERDICT: GREEN" not in out:
        print("PRECONDITION FAILED: verifier is not GREEN against the scratch tree.")
        print(out[-1800:])
        return 1
    print("precondition : GREEN\n")

    caught, missed = 0, []
    for label, rel, anchor, replacement in MUTATIONS:
        target = SCRATCH / rel
        pristine = target.read_text(encoding="utf-8")
        target.write_text(apply_mutation(pristine, anchor, replacement),
                          encoding="utf-8", newline="")
        rc, out = run()
        if rc != 0 and ("XFAIL " + label) in out:
            print("  RED   %-24s control PASSED" % label)
            caught += 1
        else:
            print("  %-5s %-24s *** CONTROL FAILED -- CHECK IS A NO-OP ***"
                  % ("GREEN" if rc == 0 else "RED", label))
            missed.append(label)
        target.write_text(pristine, encoding="utf-8", newline="")

    rc, out = run()
    print("\nfinal run    : %s" % ("GREEN" if rc == 0 else "RED"))

    # ---- owner banner controls, checked against vowner0906.py ----
    orc, oout = run_owner()
    if orc != 0 or "VERDICT: GREEN" not in oout:
        print("\nOWNER PRECONDITION FAILED: vowner is not GREEN on the scratch tree.")
        print(oout[-1500:])
        teardown()
        return 1
    print("\nowner precondition : GREEN")
    for label, rel, anchor, replacement in OWNER_MUTATIONS:
        target = SCRATCH / rel
        pristine = target.read_text(encoding="utf-8")
        target.write_text(apply_mutation(pristine, anchor, replacement),
                          encoding="utf-8", newline="")
        orc, oout = run_owner()
        if orc != 0 and ("RED   " + label) in oout:
            print("  RED   %-32s control PASSED" % label)
            caught += 1
        else:
            print("  %-5s %-32s *** CONTROL FAILED -- NO-OP ***"
                  % ("GREEN" if orc == 0 else "RED", label))
            missed.append(label)
        target.write_text(pristine, encoding="utf-8", newline="")
    orc, _ = run_owner()
    print("owner final run    : %s" % ("GREEN" if orc == 0 else "RED"))

    total = len(MUTATIONS) + len(OWNER_MUTATIONS)
    print("\ncontrols     : %d caught + %d missed = %d of %d"
          % (caught, len(missed), caught + len(missed), total))
    if missed:
        print("MISSED       : %s" % missed)
    teardown()
    ok = (caught == total and rc == 0 and orc == 0)
    print("\nVERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
