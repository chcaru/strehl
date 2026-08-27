"""Commission source_baseline_label(): prove it TRACKS the frozen rule.

A derived label is only better than a typed one if it actually moves when the
thing it derives from moves. A label that is frozen at the right answer is
indistinguishable from a literal that happens to be correct today -- and the
defect being repaired here is precisely a literal that was correct on the day
it was typed and wrong ever after.

So: four arms, each mutating the frozen rule and demanding a different label.
Every mutation is anchored on a unique full-line string and hard-errors if the
anchor does not land, because a mutation that silently fails to apply produces
a GREEN that is a statement about nothing.

The baseline is copied to TEMP and restored from that copy -- never from git,
which would reset to HEAD and discard other lanes' uncommitted work.
"""
import importlib
import json
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# orch_printready enforces its "name the arm you are certifying" guard at module
# scope, so importing it requires a real directory in argv. Satisfy the guard
# with this directory; `main()` sits behind a __main__ guard, so nothing is
# rendered or gated by the import itself.
sys.argv = ["orch_printready.py", str(HERE)]

BASELINE = HERE.parent / "V-REVIEW" / "vr_baseline.json"
ANCHOR = '  "source_baseline": "max over registered source frames"'

ARMS = [
    ("as-frozen (max => worst)", None, "master/worst-source"),
    ("min => best", '  "source_baseline": "min over registered source frames"',
     "master/best-source"),
    ("unrecognised rule prints itself", '  "source_baseline": "median of the three flattest"',
     "master/source[median of the three flattest]"),
    ("rule absent", '  "source_baseline_REMOVED": "x"',
     "master/source[BASELINE RULE UNRECORDED]"),
]


def label_now():
    """Re-import with a cleared cache so each arm re-reads the file."""
    import orch_printready
    importlib.reload(orch_printready)
    orch_printready._SOURCE_BASELINE_LABEL = None
    return orch_printready.source_baseline_label()


def main():
    original = BASELINE.read_bytes()
    backup = pathlib.Path(tempfile.gettempdir()) / "vr_baseline.commission.bak"
    shutil.copy2(BASELINE, backup)
    print("baseline : %s" % BASELINE)
    print("backup   : %s (%d bytes)" % (backup, backup.stat().st_size))

    text = original.decode("utf-8")
    if text.count(ANCHOR) != 1:
        raise SystemExit("ANCHOR NOT UNIQUE: found %d occurrences of %r"
                         % (text.count(ANCHOR), ANCHOR))

    failures = []
    try:
        for name, replacement, expect in ARMS:
            if replacement is None:
                BASELINE.write_bytes(original)
            else:
                mutated = text.replace(ANCHOR, replacement, 1)
                if mutated == text:
                    raise SystemExit("MUTATION DID NOT LAND for arm %r" % name)
                BASELINE.write_text(mutated, encoding="utf-8")
                # the arm must still be readable JSON, or we are testing the
                # except branch instead of the branch we think we are testing
                json.loads(mutated)
            got = label_now()
            ok = (got == expect)
            print("  %-34s -> %-46s %s" % (name, got, "OK" if ok else "MISMATCH"))
            if not ok:
                failures.append("%s: expected %r got %r" % (name, expect, got))
    finally:
        shutil.copy2(backup, BASELINE)

    restored = BASELINE.read_bytes()
    print("restored : %s" % ("byte-identical" if restored == original else "DIFFERS -- FIX BY HAND"))
    if restored != original:
        failures.append("baseline not restored")

    distinct = len({e for _, _, e in ARMS})
    print("distinct expected labels: %d of %d arms" % (distinct, len(ARMS)))
    if distinct != len(ARMS):
        failures.append("arms do not discriminate: %d distinct labels" % distinct)

    print()
    if failures:
        print("RED -- %d failure(s)" % len(failures))
        for f in failures:
            print("  - %s" % f)
        return 1
    print("GREEN -- label tracks the frozen rule across all %d arms" % len(ARMS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
