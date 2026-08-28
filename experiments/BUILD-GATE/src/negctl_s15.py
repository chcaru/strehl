"""Commission section 15's gates against defects they must catch.

Two gates gate section 15:

  s15_splice.py --check  re-renders the section from `s15_body.md` plus the
                         generated tables and diffs it against the report.
                         Catches anything edited in the report ALONE.

  verify_s15.py          re-derives section 15's numbers from section 15's
                         own tables, and holds a pinned copy of its verdicts.

The interesting defects are the ones that defeat the splice guard, because
that is what an author actually produces: they edit the source and
regenerate, so the report and the source agree and the diff sees nothing.
Those are the `-both` arms. A `-both` numeric defect is caught only if the
verifier genuinely RE-DERIVES rather than re-reads, and a `-both` conclusion
defect is caught only by the pinned CONCLUSIONS table.

Two controls carry identical text and must stay GREEN, so a harness that
simply failed everything could not be read as a success.

Every mutation is anchored on a unique string and hard-errors if it does not
land: a control that silently fails to plant its defect reports the
instrument as healthy, which is the failure it exists to prevent.
"""
import os
import shutil
from reportlock import ReportLock
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.abspath(os.path.join(HERE, "..", "..", "..",
                                      "docs", "research", "BUILD-GATE-4.md"))
BODY = os.path.join(HERE, "s15_body.md")
TABLES = os.path.abspath(os.path.join(HERE, "..", "gen", "s15tables.md"))
TMP = os.environ["TEMP"]

SRC = {"report": REPORT, "body": BODY, "tables": TABLES}

# (name, file-set, anchor, replacement, what it breaks)
FLIPS = [
    ("control-identical", ["report"],
     "### 15.5 What this is not",
     "### 15.5 What this is not",
     "control: identical text, must stay GREEN"),
    ("control-identical-2", ["report", "body"],
     "### 15.3 Which bands do the work: band 1 carries most of it",
     "### 15.3 Which bands do the work: band 1 carries most of it",
     "control 2: identical text in two files, must stay GREEN"),

    # --- defects the splice guard alone can catch
    ("prose-number-report-only", ["report"],
     "Lowest sharpness cell anywhere in the sweep: **0.9927x** (-0.73%).",
     "Lowest sharpness cell anywhere in the sweep: **0.9127x** (-8.73%).",
     "a prose number edited in the report alone"),

    # --- defects that DEFEAT the splice guard: source and report move together
    ("headline-blotch-both", ["report", "tables"],
     "| `bee-1-cpl` | 299 | **-25.34%** |",
     "| `bee-1-cpl` | 299 | **-35.34%** |",
     "THE REAL TEST: 15.1's headline blotch changed in the generated table "
     "AND the report; only a cross-table re-derivation catches it"),
    ("band1-share-both", ["report", "tables"],
     "| `coffee-bubbles` | -8.91% | **-6.04%** | -3.30% | **65%** |",
     "| `coffee-bubbles` | -8.91% | **-6.04%** | -3.30% | **85%** |",
     "THE REAL TEST: a band-1 share that no longer follows from its own row"),
    ("duty-band0-both", ["report", "tables"],
     "| `bee-1-cpl` | `S32` | 10.6% | 39.7% |",
     "| `bee-1-cpl` | `S32` | 18.6% | 39.7% |",
     "THE REAL TEST: breaks the band-0-unchanged claim the whole "
     "specificity argument rests on"),

    # --- conclusion flips: change no number at all
    ("verdict-b1-whole-mechanism-both", ["report", "body"],
     "real signal on their own. Band 1 is **the largest single share, not "
     "the whole",
     "real signal on their own. Band 1 is **the whole",
     "THE REAL TEST: reverses the self-correction, changing no number"),
    ("verdict-s136-both", ["report", "body"],
     "arms are what falsify it.** The null and `S32` differ only in the "
     "coarse floor,",
     "arms are what confirm it.** The null and `S32` differ only in the "
     "coarse floor,",
     "THE REAL TEST: reverses the falsification of section 13.6"),
    ("verdict-recommendation-both", ["report", "body"],
     "- **This is not a shipping recommendation.** It is an env var, "
     "default off, and",
     "- **This is a shipping recommendation.** It is an env var, "
     "default off, and",
     "THE REAL TEST: turns a disclaimer into a recommendation"),

    # --- ORCH's band rule: the licence itself must be defensible
    ("licence-flip-both", ["report", "tables"],
     "| **+0.92%** | R=1.342 MARGINAL | no |",
     "| **+0.92%** | R=1.342 MARGINAL | **yes** |",
     "THE REAL TEST: licenses a MARGINAL subject for a sharpness claim; "
     "only re-reading V-LINEAR's record catches it"),
    ("licence-count-both", ["report", "tables"],
     "**3 of 5 are qualified at 0.20-0.25 cyc/px**",
     "**4 of 5 are qualified at 0.20-0.25 cyc/px**",
     "THE REAL TEST: overstates how many subjects are licensed"),
    ("licence-range-both", ["report", "tables"],
     "across the 3 licensed subjects it spans +0.16% to +2.25%",
     "across the 3 licensed subjects it spans +0.42% to +2.25%",
     "THE REAL TEST: a restricted range that does not follow from the "
     "licensed rows"),
    ("verdict-compose-both", ["report", "tables"],
     "**The two disqualifications compose.** Band qualification asks",
     "**The two disqualifications are the same test.** Band qualification "
     "asks",
     "THE REAL TEST: collapses two independent tests into one, changing "
     "no number"),
    ("verdict-blotch-scope-both", ["report", "body"],
     "The blotch column is unaffected by this rule. Blotch is `sigma_mid` "
     "over",
     "The blotch column is withdrawn by this rule. Blotch is `sigma_mid` "
     "over",
     "THE REAL TEST: widens the withdrawal to a column the rule does not "
     "reach"),
    ("anchor-drift-both", ["report", "tables"],
     "Grain spans -1.08% to +0.68% across all subjects",
     "Grain spanned -1.08% to +0.68% across all subjects",
     "THE REAL TEST: a claim that silently drops OUT OF COVERAGE. Every "
     "number stays correct and no verdict moves; only making an unmatched "
     "anchor fatal catches it"),
]


def read(p):
    return open(p, encoding="utf-8", errors="strict").read()


def write(p, t):
    open(p, "w", encoding="utf-8", newline="").write(t)


def plant(path, old, new):
    t = read(path)
    n = t.count(old)
    if n != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND (%d occurrences) in %s:\n"
                         "  %r" % (n, os.path.basename(path), old[:70]))
    write(path, t.replace(old, new, 1))


def gates():
    a = subprocess.run([sys.executable, os.path.join(HERE, "s15_splice.py"),
                        "--check"], capture_output=True, cwd=HERE)
    b = subprocess.run([sys.executable, os.path.join(HERE, "verify_s15.py")],
                       capture_output=True, cwd=HERE)
    return a.returncode == 0, b.returncode == 0


def main():
    bak = {k: os.path.join(TMP, "negctl_s15_%s.bak" % k) for k in SRC}
    for k in SRC:
        shutil.copy2(SRC[k], bak[k])
    print("backed up %d files to %s\n" % (len(SRC), TMP))

    base = gates()
    print("baseline: splice=%s verify=%s\n"
          % ("OK" if base[0] else "RED", "OK" if base[1] else "RED"))
    if not all(base):
        for k in SRC:
            shutil.copy2(bak[k], SRC[k])
        print("baseline is not green; aborting so a pre-existing failure is "
              "not read as a caught defect.")
        return 1

    caught = missed = ctl_bad = 0
    rows = []
    try:
        for name, files, old, new, what in FLIPS:
            control = (old == new)
            for fl in files:
                plant(SRC[fl], old, new)
            sp, ve = gates()
            by = [n for n, ok in (("splice", sp), ("verify", ve)) if not ok]
            if control:
                good = sp and ve
                verdict = "GREEN (correct)" if good else "CONTROL FAILED"
                ctl_bad += 0 if good else 1
            elif sp and ve:
                verdict = "**MISSED**"
                missed += 1
            else:
                verdict = "caught by %s" % "+".join(by)
                caught += 1
            rows.append((name, what, verdict))
            print("%-32s %s" % (name, verdict))
            for fl in files:
                shutil.copy2(bak[fl], SRC[fl])
    finally:
        for k in SRC:
            shutil.copy2(bak[k], SRC[k])

    same = all(read(SRC[k]) == read(bak[k]) for k in SRC)
    post = gates()
    print("\nrestored byte-identical: %s   post-restore: splice=%s verify=%s"
          % (same, "OK" if post[0] else "RED", "OK" if post[1] else "RED"))

    real = [x for x in FLIPS if x[3] != x[2]]
    print("\n%d caught / %d MISSED of %d defects  (%d controls, %d failures)"
          % (caught, missed, len(real), len(FLIPS) - len(real), ctl_bad))
    print("\ndetail:")
    for name, what, verdict in rows:
        print("  %-32s %-72s %s" % (name, what[:72], verdict))

    ok = missed == 0 and ctl_bad == 0 and same and all(post)
    print("\n%s" % ("COMMISSIONED: every planted defect was caught."
                    if ok else
                    "NOT COMMISSIONED: a defect was missed or the harness "
                    "itself failed."))
    return 0 if ok else 1


if __name__ == "__main__":
    with ReportLock("negctl_s15.py"):
        sys.exit(main())
