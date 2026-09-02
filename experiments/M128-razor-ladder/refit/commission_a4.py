"""
Commissioning for check_a4.py.

check_a4.py returned 42/42 GREEN on its first run. Under house rule 9 that is
not evidence of anything: a checker whose anchors do not resolve returns exactly
the same green as one that verified every number. This script plants known
defects in a COPY of the preregistration and requires the checker to go RED on
each one.

TWO ANCHOR STRATEGIES, FOR TWO KINDS OF PLANT
---------------------------------------------
  NUMERIC   Mutate a digit of a value. The anchor is the literal value string,
            required to occur EXACTLY ONCE inside the A4 region. A number never
            spans a line break, so a unique literal is safe here, and the
            uniqueness requirement is what makes the mutation unambiguous.

  PHRASE    Delete or corrupt a sentence. Prose WRAPS, so a literal anchor
            spanning a newline silently fails to match and the plant is inert --
            producing a green that looks like a caught defect but is really a
            defect that was never planted. Phrase anchors are therefore compiled
            to a regex joining tokens on \\s+, matched against the RAW text.

  Every plant hard-errors if its anchor does not resolve exactly once. An
  unplanted defect must never be able to masquerade as a caught one.

SAFETY
------
  The real PREREGISTRATION.md is never modified. Each plant is applied to a
  fresh temp copy and the checker is pointed at it via A4_PATH. Nothing here
  touches git, and in particular nothing runs `git checkout --`.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
SRC = os.path.join(LANE, "PREREGISTRATION.md")
CHECK = os.path.join(HERE, "check_a4.py")

with open(SRC, encoding="utf-8") as f:
    ORIG = f.read()
A4_AT = ORIG.find("### Amendment A4")
assert A4_AT > 0, "Amendment A4 not found"

# ---------------------------------------------------------------- plant tables
# (label, value-as-written, mutated-value)
NUMERIC = [
    ("refit w isotonic", "19.05 / 17.35", "19.55 / 17.35"),
    ("refit w erf", "19.05 / 17.35", "19.05 / 17.85"),
    ("sigma isotonic", "**2.03**", "**2.63**"),
    ("sigma erf", "**2.50 sigma**", "**2.90 sigma**"),
    ("w95 interval", "3.7-25.2 um", "3.7-22.2 um"),
    ("sharp-edge prediction", "= 1.964`", "= 1.164`"),
    ("ratio isotonic", "are **0.79** and", "are **0.59** and"),
    ("ratio erf", "and **0.90**. The rise", "and **0.70**. The rise"),
    ("sensor pitch", "the 5.12 um pixel aperture", "the 6.12 um pixel aperture"),
    ("sublattice pitch", "full** 10.24 um green-sublattice",
     "full** 12.24 um green-sublattice"),
    ("pixel-aperture rise", "a 4.10 um rise", "a 4.90 um rise"),
    ("sampling contribution", "contributes 8.19 um", "contributes 8.99 um"),
    ("combined floor", "floor of **9.16 um**", "floor of **9.96 um**"),
    ("w_physical isotonic", "**w_physical = 16.70 um**", "**w_physical = 15.70 um**"),
    ("w_physical erf", "and **14.74 um** (erf)", "and **13.74 um** (erf)"),
    ("commission tally", "commissioned, 6/6.**", "commissioned, 5/6.**"),
    ("flat-plant closed form", "**1.4681 sigma**", "**1.8681 sigma**"),
    ("flat-plant grid", "returned 1.47 sigma", "returned 1.77 sigma"),
    ("real decreasing sigma", "excludes it at 2.53 sigma", "excludes it at 2.93 sigma"),
    ("turn-0 isotonic rise", "**19.848 um** by isotonic", "**19.148 um** by isotonic"),
    ("turn-0 erf rise", "**19.326 um** by an erf", "**19.826 um** by an erf"),
    ("plateaus", "3236.7 and 718.0 DN", "3236.7 and 918.0 DN"),
    ("contrast", "contrast 2518.6 DN", "contrast 2118.6 DN"),
    ("ladder f/5.6", "| 5.6 | 20.86 +/- 5.6 |", "| 5.6 | 21.86 +/- 5.6 |"),
    ("ladder f/8", "| 8 | 19.91 +/- 5.3 |", "| 8 | 19.91 +/- 5.9 |"),
    ("ladder f/11", "| 11 | 16.50 +/- 5.4 |", "| 11 | 16.50 +/- 5.7 |"),
    ("template corr", "(0.811 and 0.728;", "(0.911 and 0.728;"),
    ("plateau ratios", "ratios 4.52 / 4.60 / 4.39)", "ratios 4.52 / 4.90 / 4.39)"),
    ("source frame", "`DSC00063.ARW`", "`DSC00064.ARW`"),
    ("locus rows", "rows `[254:286)`", "rows `[254:826)`"),
    ("raggedness", "`-31.70%` on its raggedness", "`-33.70%` on its raggedness"),
]

# (label, phrase-to-remove) -- matched with \s+ between tokens, on RAW text
PHRASE = [
    ("universal negative refuted", "universal negative is refuted"),
    ("nothing retracted", "nothing here is being retracted"),
    ("verifier had no code", "**not** my reduction code"),
    ("C2 error disclosed", "the bar was mine, not the instrument"),
    ("bar not relaxed", "was not relaxed to make the control pass"),
    ("inference not measurement", "checks the inference, not the measurement"),
    ("verifier wrote no files", "verifier reported no files"),
    ("verifier caveat kept", "only moderate discrimination"),
    ("claim not upgraded", "deliberately does not make one"),
    ("two disqualifications", "two independent disqualifications"),
]

results = []


def run_checker(path):
    env = dict(os.environ, A4_PATH=path, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, CHECK], capture_output=True, text=True,
                       cwd=HERE, env=env)
    return p.returncode, p.stdout


tmpdir = tempfile.mkdtemp(prefix="a4commission_")
print("COMMISSIONING check_a4.py")
print("plants applied to copies under %s" % tmpdir)
print("=" * 74)

def wrap_re(phrase):
    """Compile a phrase to a regex joining tokens on \\s+.

    Prose wraps. A literal anchor spanning a newline matches nothing, the plant
    is never applied, and the checker returns green -- which is indistinguishable
    from a caught defect unless the miss is detected here.
    """
    return re.compile(r"\s+".join(re.escape(t) for t in phrase.split()))


def resolve_once(phrase, label, kind):
    pat = wrap_re(phrase)
    hits = list(pat.finditer(ORIG, A4_AT))
    if len(hits) != 1:
        print("FATAL: %s anchor %r matched %d times in A4 (need exactly 1)"
              % (kind, label, len(hits)))
        print("       INERT PLANT -- this would have produced a false CAUGHT.")
        sys.exit(2)
    return hits[0]


def retoken(matched, old, new):
    """Rebuild `matched` with `new`'s tokens, preserving its original whitespace.

    The matched span may contain a line break. Substituting token-by-token keeps
    that break exactly where it was, so the planted file differs from the
    original in the value alone and not in its wrapping.
    """
    to, tn = old.split(), new.split()
    assert len(to) == len(tn), "token count differs: %r vs %r" % (old, new)
    parts = re.split(r"(\s+)", matched)
    out, i = [], 0
    for p in parts:
        if p.strip() == "":
            out.append(p)
        else:
            out.append(tn[i])
            i += 1
    assert i == len(tn), "token walk mismatch for %r" % old
    return "".join(out)


for label, old, new in NUMERIC:
    m = resolve_once(old, label, "numeric")
    mutated = ORIG[:m.start()] + retoken(m.group(0), old, new) + ORIG[m.end():]
    if mutated == ORIG:
        print("FATAL: plant %r produced no change -- inert." % label)
        sys.exit(2)
    path = os.path.join(tmpdir, "n_%s.md" % re.sub(r"\W+", "_", label))
    with open(path, "w", encoding="utf-8") as f:
        f.write(mutated)
    rc, _ = run_checker(path)
    caught = rc != 0
    results.append((label, caught))
    print("  %-26s %s" % (label, "CAUGHT" if caught else "*** MISSED ***"))

for label, phrase in PHRASE:
    m = resolve_once(phrase, label, "phrase")
    mutated = ORIG[:m.start()] + "[removed by commissioning]" + ORIG[m.end():]
    path = os.path.join(tmpdir, "p_%s.md" % re.sub(r"\W+", "_", label))
    with open(path, "w", encoding="utf-8") as f:
        f.write(mutated)
    rc, _ = run_checker(path)
    caught = rc != 0
    results.append((label, caught))
    print("  %-26s %s" % (label, "CAUGHT" if caught else "*** MISSED ***"))

print("-" * 74)
rc, out = run_checker(SRC)
null_ok = rc == 0
print("  %-26s %s" % ("NULL (unmodified)", "GREEN" if null_ok else "*** RED ***"))

caught_n = sum(1 for _, c in results if c)
total_n = len(results)
ok = caught_n == total_n and null_ok
print("=" * 74)
print("plants: %d   caught: %d   missed: %d   null: %s"
      % (total_n, caught_n, total_n - caught_n, "GREEN" if null_ok else "RED"))
print("STATUS: %s" % ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
shutil.rmtree(tmpdir, ignore_errors=True)
sys.exit(0 if ok else 1)
