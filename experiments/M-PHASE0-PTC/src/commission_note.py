"""
Commissioning battery for check_note.py.

WHY THIS EXISTS
---------------
check_note.py returned 47/47 GREEN on its first run and has never failed. A
checker that has never fired may be a silent no-op -- the summary looks identical
whether every figure is right or whether nothing was examined. This script proves
each check can fire by planting the exact defect it targets.

THE TWO RULES THAT MAKE A PLANT MEANINGFUL
------------------------------------------
1. ANCHOR ON A UNIQUE FULL STRING AND HARD-ERROR IF IT DOES NOT LAND.
   A bare `text.replace(x, y, 1)` that silently matches nothing produces a GREEN
   run that reads exactly like a caught defect. Every plant below asserts its
   anchor occurs, and asserts the mutation actually changed the text.

2. NEVER TOUCH THE REAL FILE. Each plant is applied to a COPY in a temp
   directory; the checker is pointed at the copy via NOTE_PATH. The tracked note
   is never written and never reverted -- there is no `git checkout --` anywhere
   in this lane.

A plant that the checker does NOT catch is reported as MISSED, and the battery
exits non-zero. MISSED means the corresponding check is decorative.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(LANE))
NOTE = os.path.join(ROOT, "docs", "research", "M-PHASE0-PTC.md")
CHECKER = os.path.join(HERE, "check_note.py")

with open(NOTE, encoding="utf-8") as f:
    ORIGINAL = f.read()

# (label, anchor -> replacement).  Each targets one named check.
PLANTS = [
    ("S1 M90 CI digit",
     "is **±0.0642%**.", "is **±0.0643%**."),
    ("S1 inter-method disagreement",
     "They differ by **1.3342%**", "They differ by **1.3352%**"),
    ("S1 ratio to bar",
     "— **20.8× the bar**", "— **20.9× the bar**"),
    ("S1 band width",
     "**1.2 pp wide — 19×", "**1.3 pp wide — 19×"),
    ("S3 per-stack g bee-1",
     "| `bee-1` | 100 | 0.222641 |", "| `bee-1` | 100 | 0.222642 |"),
    ("S3 per-stack delta bee-3",
     "| 0.222805 | **+0.765%** |", "| 0.222805 | **+0.766%** |"),
    ("S3 inside-CI count",
     "**Inside B1's named CI: 0 of 6.", "**Inside B1's named CI: 1 of 6."),
    ("S3 inside-band count",
     "Inside M90's own stated band: 5 of 6.**", "Inside M90's own stated band: 4 of 6.**"),
    ("S3 median internal",
     "agree to a **median 0.224%**", "agree to a **median 0.225%**"),
    ("S3 external scatter",
     "scatter is **9.896 pp**", "scatter is **9.897 pp**"),
    ("S3 external/internal ratio",
     "External/internal = **44.3×**", "External/internal = **44.4×**"),
    ("S4 negative intercept fraction",
     "rows = 68.8%**, range", "rows = 68.9%**, range"),
    ("S4 intercept range low",
     "range **−548.41 to", "range **−548.42 to"),
    ("S5 ungated width",
     "| ungated | 6 | −7.532% … +2.365% | 9.896 pp |",
     "| ungated | 6 | −7.532% … +2.365% | 9.897 pp |"),
    ("S5 gated width",
     "| **+0.691% … +2.365%** | **1.674 pp** |",
     "| **+0.691% … +2.365%** | **1.675 pp** |"),
    ("S5 collapse factor",
     "**Collapse factor 5.9×.**", "**Collapse factor 6.9×.**"),
    ("S6 armA mean g",
     "| **nothing** | 0.222723 |", "| **nothing** | 0.222724 |"),
    ("S6 armA vs M90",
     "| **+0.728%** | −0.616% |", "| **+0.729%** | −0.616% |"),
    ("S6 armA agreement",
     "agree with each other to **0.074 pp**", "agree with each other to **0.075 pp**"),
    ("S6 armA position",
     "land **54% of the way**", "land **55% of the way**"),
    ("S6 armB mean g",
     "| 0.224422 | +1.496% |", "| 0.224423 | +1.496% |"),
    ("S6 arms differ",
     "**The arms differ by 0.768 pp,", "**The arms differ by 0.769 pp,"),
    # structural plants
    ("STRUCT errors section removed",
     "## 7. My own errors, disclosed", "## 7. Notes"),
    ("STRUCT scope limit removed",
     "did **not** re-derive", "did re-derive"),
    ("STRUCT prereg weakness removed",
     "author-attested, not commit-attested", "fully commit-attested"),
    ("STRUCT observation label removed",
     "It carries no pass/fail.", "It is conclusive."),
    ("STRUCT bare pipe splits a row",
     "| **CONSIST** | 5 | **+0.691% … +2.365%** | **1.674 pp** |",
     "| **CONSIST** | 5 | **+0.691% … |2.365%** | **1.674 pp** |"),
]

tmpdir = tempfile.mkdtemp(prefix="m-phase0-ptc-commission-")
tmpnote = os.path.join(tmpdir, "M-PHASE0-PTC.md")

caught, missed, bad_anchor = [], [], []

print("commissioning check_note.py -- %d plants" % len(PLANTS))
print("=" * 70)

for label, anchor, repl in PLANTS:
    if anchor not in ORIGINAL:
        bad_anchor.append(label)
        print("%-34s ANCHOR NOT FOUND -- plant is inert, not a pass" % label)
        continue
    mutated = ORIGINAL.replace(anchor, repl, 1)
    if mutated == ORIGINAL:
        bad_anchor.append(label)
        print("%-34s MUTATION DID NOT CHANGE TEXT" % label)
        continue
    with open(tmpnote, "w", encoding="utf-8") as f:
        f.write(mutated)
    env = dict(os.environ, NOTE_PATH=tmpnote, PYTHONIOENCODING="utf-8")
    rc = subprocess.run([sys.executable, CHECKER], env=env,
                        capture_output=True, text=True).returncode
    if rc != 0:
        caught.append(label)
    else:
        missed.append(label)
        print("%-34s MISSED -- the checker passed a planted defect" % label)

# control: the unmutated file must still be GREEN through the same path
shutil.copyfile(NOTE, tmpnote)
env = dict(os.environ, NOTE_PATH=tmpnote, PYTHONIOENCODING="utf-8")
rc_clean = subprocess.run([sys.executable, CHECKER], env=env,
                          capture_output=True, text=True).returncode
shutil.rmtree(tmpdir, ignore_errors=True)

print("")
print("=" * 70)
print("plants %d   CAUGHT %d   MISSED %d   INERT(anchor) %d   (sum %d)"
      % (len(PLANTS), len(caught), len(missed), len(bad_anchor),
         len(caught) + len(missed) + len(bad_anchor)))
print("null control (unmutated copy through the same path): %s"
      % ("GREEN" if rc_clean == 0 else "NOT GREEN -- battery is unsound"))
ok = (not missed) and (not bad_anchor) and rc_clean == 0
print("VERDICT: %s" % ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
sys.exit(0 if ok else 1)
