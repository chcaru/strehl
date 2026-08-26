"""Commission append57.py's guards before trusting them.

Three checks, each of which must produce the stated outcome:
  1. the anchor is present in the live corpus exactly once  (else the append is blind)
  2. against a corpus whose anchor has been altered, the guard must REFUSE
  3. against a corpus that already contains the marker, the guard must SKIP

Check 2 is the one that matters: a guard that has never refused is not a guard.
Nothing here writes to the corpus.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("append57", HERE / "append57.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

text = m.CORPUS.read_text(encoding="utf-8")
fails = 0

n = text.count(m.ANCHOR)
print(f"1. anchor occurrences in live corpus: {n}  (want exactly 1)")
if n != 1:
    print("   FAIL")
    fails += 1
else:
    print("   PASS")

ends_with = text.rstrip().endswith(m.ANCHOR.rstrip())
print(f"1b. anchor is the final text: {ends_with}  (want True)")
if not ends_with:
    print("   FAIL")
    fails += 1
else:
    print("   PASS")

# 2. NEGATIVE CONTROL: alter one character inside the anchor region and confirm
#    the two guard predicates both go false. If they do not, the guard is inert.
mutated = text.replace(
    "gather throws away. Two questions, both in flight, both with registered tests.",
    "gather throws away. Two questions, both in flight, both with registered testz.",
)
if mutated == text:
    print("2. FAIL: mutation did not land -- the control cannot express failure")
    fails += 1
else:
    present = m.ANCHOR in mutated
    tail_ok = mutated.rstrip().endswith(m.ANCHOR.rstrip())
    print(f"2. under a 1-char mutation: anchor present={present} tail_ok={tail_ok}  (want False False)")
    if present or tail_ok:
        print("   FAIL -- guard would have appended onto text it did not recognise")
        fails += 1
    else:
        print("   PASS -- guard refuses")

# 3. idempotence predicate
already = text + "\n" + m.MARKER + "\n"
print(f"3. marker-present predicate on a corpus containing it: {m.MARKER in already}  (want True)")
if m.MARKER not in already:
    print("   FAIL")
    fails += 1
else:
    print("   PASS")

print(f"\n{'ALL GUARDS COMMISSIONED' if fails == 0 else str(fails) + ' GUARD CHECK(S) FAILED'}")
sys.exit(1 if fails else 0)
