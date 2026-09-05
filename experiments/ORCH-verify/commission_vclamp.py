"""Commission vclamp.py by planting the exact defects it is supposed to catch.

Each arm mutates one file, re-runs the checker, and asserts the expected colour.
Every mutation anchors on a string that must occur EXACTLY ONCE; a miss is a hard
error, never a silent pass, because an unplanted defect and a caught defect both
look like a red run otherwise.

Restores come from copies taken into $TEMP before any mutation and are SHA-verified
afterwards. `git checkout --` is never used: it reverts to HEAD and would destroy
uncommitted work in this shared tree.
"""
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECKER = ROOT / "experiments" / "ORCH-verify" / "vclamp.py"
DECISION = ROOT / "docs" / "research" / "ORCH-clamp-default-decision.md"
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_checker():
    proc = subprocess.run(
        [sys.executable, str(CHECKER)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return ("GREEN" if proc.returncode == 0 else "RED"), proc.stdout


# label, file, needle (must occur exactly once), replacement, expected colour
ARMS = [
    ("A: corrected anchor :1631 deleted", DECISION,
     "`docs/proposals/2026-09-sota-scorecard.md:1629-1631` — **\"Known defeat.**",
     "`docs/proposals/2026-09-sota-scorecard.md` — **\"Known defeat.**",
     "RED"),
    ("B: wrong anchor reintroduced as live citation", DECISION,
     "The correct anchors are `:1631` (known defeat) and",
     "See also `docs/proposals/2026-09-sota-scorecard.md:1573-1582`. "
     "The correct anchors are `:1631` (known defeat) and",
     "RED"),
    ("C: M4 co-control note removed", DECISION,
     "silently drops M4",
     "omits a detail",
     "RED"),
    ("D: source quote mutated in the scorecard", SCORECARD,
     "absent, M8 may prove only this internal invariant, not SOTA.",
     "absent, M8 may prove only this internal property, not SOTA.",
     "RED"),
    ("E (inert): unrelated prose edit", DECISION,
     "## 1. The decision",
     "## 1. The decision to be taken",
     "GREEN"),
]


def main():
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="vclamp-commission-"))
    originals = {}
    for path in {DECISION, SCORECARD}:
        backup = tmpdir / path.name
        shutil.copy2(path, backup)
        originals[path] = (backup, sha(path))

    baseline, _ = run_checker()
    if baseline != "GREEN":
        print("ABORT: baseline is not GREEN; commissioning is meaningless")
        return 2

    caught = missed = inert_ok = inert_bad = 0
    try:
        for label, path, needle, replacement, expected in ARMS:
            text = path.read_text(encoding="utf-8")
            n = text.count(needle)
            if n != 1:
                raise SystemExit(
                    f"MUTATION TARGET NOT FOUND: {label!r} anchor matched {n} "
                    f"times in {path.name}, expected exactly 1"
                )
            path.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
            colour, out = run_checker()
            ok = colour == expected
            if expected == "RED":
                if ok:
                    caught += 1
                else:
                    missed += 1
            else:
                if ok:
                    inert_ok += 1
                else:
                    inert_bad += 1
            print(f"  [{'ok ' if ok else 'BAD'}] {label}: got {colour}, expected {expected}")
            # restore before the next arm
            shutil.copy2(originals[path][0], path)
    finally:
        for path, (backup, original_sha) in originals.items():
            shutil.copy2(backup, path)
            if sha(path) != original_sha:
                print(f"  RESTORE FAILED for {path}")
                return 3
        shutil.rmtree(tmpdir, ignore_errors=True)

    final, _ = run_checker()
    total = caught + missed + inert_ok + inert_bad
    print()
    print(f"arms planted      {len(ARMS)}")
    print(f"caught            {caught}")
    print(f"missed            {missed}")
    print(f"inert stayed GREEN{inert_ok:>2}")
    print(f"inert went RED    {inert_bad}")
    print(f"accounted         {total} of {len(ARMS)}")
    print(f"restored baseline {final}")
    good = (missed == 0 and inert_bad == 0 and total == len(ARMS) and final == "GREEN")
    print("COMMISSIONED" if good else "NOT COMMISSIONED")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
