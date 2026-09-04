"""Commission the STATUS 2.9.66 cross-document quote checks.

These four checks read files that *other lanes own and are actively editing*.
Mutating them in the live tree would race a lane's commit and could corrupt its
work, so this harness builds a scratch repo root in TEMP, confirms the verifier
is GREEN against it, and plants each defect there instead. The live tree is
never written.

v2954.py takes a repo root as argv[1], which is what makes this possible.
"""
import shutil
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
        if anchor not in pristine:
            raise SystemExit("MUTATION TARGET NOT FOUND for %r in %s: %r"
                             % (label, rel, anchor))
        if pristine.count(anchor) != 1:
            raise SystemExit("MUTATION ANCHOR NOT UNIQUE for %r in %s (%d hits)"
                             % (label, rel, pristine.count(anchor)))
        target.write_text(pristine.replace(anchor, replacement, 1),
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
    total = len(MUTATIONS)
    print("\ncontrols     : %d caught + %d missed = %d of %d"
          % (caught, len(missed), caught + len(missed), total))
    if missed:
        print("MISSED       : %s" % missed)
    teardown()
    ok = (caught == total and rc == 0)
    print("\nVERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
