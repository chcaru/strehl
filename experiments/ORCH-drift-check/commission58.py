"""Commission append58.py: prove its guards can actually refuse.

A guard that has never been observed to refuse is not a guard, it is a comment.
This runs append58.py against constructed copies of the corpus in a temporary
workspace -- never against the real file -- and requires each guard to fire.

Cases:
  1 happy path        : correct anchor            -> rc=0 and the file GROWS
  2 idempotence       : run twice                 -> rc=0 and the file does NOT grow
  3 tail mutated      : anchor's last line broken -> rc=1, refuses
  4 tail appended to  : extra line after anchor   -> rc=1, refuses
  5 missing file      : no corpus at all          -> rc=1, refuses

Case 3's mutation is anchored on a UNIQUE full line and asserted to have
landed. A str.replace that silently matches nothing produces an unmodified file,
the append succeeds, and the case reports PASS for a guard that never ran --
a green that means the opposite of what it appears to mean.
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
REAL = REPO / "docs" / "research" / "ORCH-veiling.md"
SCRIPT = REPO / "experiments" / "ORCH-drift-check" / "append58.py"

# a unique full line inside the section 57 anchor
MUT_FROM = "accessors would have been exactly the error this section is about, in reverse.\n"
MUT_TO = "accessors would have been exactly the error this section is about, inverted.\n"

results = []


def run(cwd):
    p = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(cwd), capture_output=True, text=True,
    )
    return p.returncode, (p.stdout + p.stderr).strip()


def case(name, setup, want_rc, want_grow):
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        d = work / "docs" / "research"
        d.mkdir(parents=True)
        target = d / "ORCH-veiling.md"
        setup(target)
        before = target.stat().st_size if target.exists() else -1
        rc, out = run(work)
        after = target.stat().st_size if target.exists() else -1
        grew = after > before
        ok = (rc == want_rc) and (grew == want_grow)
        results.append((name, ok, rc, want_rc, grew, want_grow, out.splitlines()[0] if out else ""))


def plain(target):
    shutil.copy2(REAL, target)


def twice(target):
    shutil.copy2(REAL, target)
    subprocess.run([sys.executable, str(SCRIPT)], cwd=str(target.parents[2]),
                   capture_output=True, text=True)


def mutated(target):
    text = REAL.read_text(encoding="utf-8")
    if MUT_FROM not in text:
        raise SystemExit(
            "MUTATION TARGET NOT FOUND -- the anchor line has changed.\n"
            f"  looked for: {MUT_FROM!r}\n"
            "Refusing to run: a mutation that does not land makes this case\n"
            "report PASS for a guard that was never exercised."
        )
        # unreachable, but the raise above is the point
    n = text.count(MUT_FROM)
    if n != 1:
        raise SystemExit(f"MUTATION TARGET NOT UNIQUE -- {n} occurrences; refusing")
    target.write_text(text.replace(MUT_FROM, MUT_TO), encoding="utf-8")


def appended(target):
    target.write_text(REAL.read_text(encoding="utf-8") + "\nstray line\n", encoding="utf-8")


def absent(target):
    pass


def main():
    if not REAL.exists():
        print(f"FAIL: {REAL} not found")
        return 1

    case("1 happy path      ", plain, 0, True)
    # case 2 needs the second run inside the same workspace; do it inline
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        d = work / "docs" / "research"
        d.mkdir(parents=True)
        t = d / "ORCH-veiling.md"
        shutil.copy2(REAL, t)
        run(work)
        mid = t.stat().st_size
        rc, out = run(work)
        after = t.stat().st_size
        ok = rc == 0 and after == mid
        results.append(("2 idempotence     ", ok, rc, 0, after > mid, False,
                        out.splitlines()[0] if out else ""))
    case("3 tail mutated    ", mutated, 1, False)
    case("4 tail appended to", appended, 1, False)
    case("5 missing file    ", absent, 1, False)

    print()
    bad = 0
    for name, ok, rc, wrc, grew, wgrew, first in results:
        tag = "PASS" if ok else "FAIL"
        if not ok:
            bad += 1
        print(f"  {tag}  {name}  rc={rc} (want {wrc})  grew={grew} (want {wgrew})  | {first}")
    print()
    if bad:
        print(f"COMMISSIONING FAILED: {bad}/{len(results)} cases wrong. Do not use append58.py.")
        return 1
    print(f"COMMISSIONED: {len(results)}/{len(results)} cases behaved as specified.")
    print("Every guard was observed to refuse. append58.py may be used.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
