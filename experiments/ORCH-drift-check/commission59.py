"""Commission append59.py: exercise every guard and observe it refuse.

A guard that has never been shown to refuse is not a guard. This harness runs
append59 against a disposable copy of the corpus in a temp directory -- the
real document is never touched during commissioning -- and requires each of the
five guards to fire with the expected verdict.

Per the corpus rule on negative controls: each mutation is anchored on a unique
full-line string and the harness hard-errors if the mutation does not land, so
a guard cannot be credited for refusing an input that was never actually
malformed.
"""
import importlib.util
import io
import contextlib
import os
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
REAL_DOC = REPO / "docs" / "research" / "ORCH-veiling.md"
MODULE = HERE / "append59.py"


def load_module():
    spec = importlib.util.spec_from_file_location("append59_under_test", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(mod):
    """Run mod.main(), returning (rc, captured stdout)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.main()
    return rc, buf.getvalue()


def stage(tmp: pathlib.Path, text: str) -> pathlib.Path:
    doc = tmp / "docs" / "research" / "ORCH-veiling.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(text, encoding="utf-8")
    return doc


def main() -> int:
    if not REAL_DOC.exists():
        print(f"ABORT: {REAL_DOC} missing")
        return 1
    pristine = REAL_DOC.read_text(encoding="utf-8")
    results = []

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            # --- Case A: document does not exist at all -------------------
            mod = load_module()
            rc, out = run(mod)
            results.append(("A missing document", rc, out.strip().splitlines()[:1]))

            # --- Case B: healthy input, happy path ------------------------
            stage(tmp, pristine)
            mod = load_module()
            rc_ok, out_ok = run(mod)
            results.append(("B happy path", rc_ok, out_ok.strip().splitlines()[:1]))
            grown = (tmp / "docs" / "research" / "ORCH-veiling.md").read_text(
                encoding="utf-8"
            )
            if rc_ok != 0:
                print("ABORT: happy path did not succeed; nothing else is meaningful")
                for r in results:
                    print(r)
                return 1
            if "## 59." not in grown:
                print("ABORT: happy path returned 0 but wrote no section 59")
                return 1

            # --- Case C: idempotence -- section 59 already present ---------
            mod = load_module()
            rc, out = run(mod)
            results.append(("C already present", rc, out.strip().splitlines()[:1]))

            # --- Case D: anchor does not match ----------------------------
            # Mutation anchored on a unique full line; hard-error if absent.
            needle = "will answer a question nobody asked.\n"
            if pristine.count(needle) != 1:
                print(
                    f"ABORT: mutation target occurs {pristine.count(needle)} times, "
                    "not once -- the control would be unanchored"
                )
                return 1
            mutated = pristine[: -len(needle)] + "will answer a question nobody posed.\n"
            if mutated == pristine:
                print("ABORT: anchor mutation did not land")
                return 1
            stage(tmp, mutated)
            mod = load_module()
            rc, out = run(mod)
            results.append(("D wrong anchor", rc, out.strip().splitlines()[:1]))

            # --- Case E: result would not grow ----------------------------
            stage(tmp, pristine)
            mod = load_module()
            mod.BODY = ""
            rc, out = run(mod)
            results.append(("E empty body", rc, out.strip().splitlines()[:1]))
        finally:
            os.chdir(cwd)

    # The real document must be untouched by commissioning.
    after = REAL_DOC.read_text(encoding="utf-8")
    untouched = after == pristine

    expected = {
        "A missing document": 1,
        "B happy path": 0,
        "C already present": 1,
        "D wrong anchor": 1,
        "E empty body": 1,
    }

    print("case                 rc  expected  verdict  first line")
    ok = True
    for name, rc, first in results:
        exp = expected[name]
        good = rc == exp
        ok = ok and good
        msg = first[0] if first else ""
        print(f"{name:<20} {rc:>2}  {exp:>8}  {'PASS' if good else 'FAIL':<7}  {msg}")

    print()
    print(f"real document untouched by commissioning: {untouched}")
    if not untouched:
        ok = False

    refused = sum(1 for n, rc, _ in results if expected[n] == 1 and rc == 1)
    print(f"guards observed to refuse: {refused}/4   accepted: "
          f"{sum(1 for n, rc, _ in results if expected[n] == 0 and rc == 0)}/1")
    print("COMMISSIONED" if ok else "NOT COMMISSIONED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
