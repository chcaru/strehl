"""Commission `verify_bands_doc.py` by planting defects it must catch.

WHY THIS FILE EXISTS
--------------------
`verify_bands_doc.py` version 1 reported **40/40 GREEN on a document that had
been corrupted**, because every R is quoted in three separate tables and the
check tested presence-in-the-whole-file.  A green from an uncommissioned
verifier is not evidence; it is the absence of evidence wearing the same colour.

So the verifier is re-commissioned here every time it changes.  Each arm plants
one defect, runs the verifier, and requires a NON-ZERO exit.  A defect that
still reads GREEN is a hole in the instrument and is reported as MISSED.

TWO DEFECTS IN THE VERIFIER WERE FOUND BY RUNNING IT, NOT BY READING IT:

  1. Row selection was POSITIONAL (`rows[0]`, `rows[1]` of the rows whose first
     cell is the subject).  Adding §9.1 and §10 -- two further subject-keyed
     tables -- silently made `rows[0]` the PROSE row, and all 50 round-2 checks
     read WRONG against a row that never carried numbers.  Fixed by anchoring on
     row SHAPE and requiring exactly one match.
  2. Globbing `bandsweep-far20*.json` pulled in the §6.1 reproduction control,
     which disagrees with the canonical record BY DESIGN, and it shadowed the
     real `leaf-2-cpl` record.  The document was right and the loader was wrong.

Both are the same class as the defect this file was written for: a check
satisfied by the wrong instance of the right-looking thing.

SAFETY
------
The document is copied to %TEMP% and restored from that copy.  It is never
reverted with `git checkout --`, which reverts to HEAD and would destroy the
uncommitted round-2 sections outright.

Every mutation is anchored on a UNIQUE FULL LINE and hard-errors if the anchor
is not found exactly once.  An unanchored `replace(x, y, 1)` can land on the
first coincidental occurrence, in which case the arm is measuring nothing and
its RED is meaningless.

Run:  python commission_verify_doc.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
DOC = os.path.join(_ROOT, "docs", "research", "V-LINEAR-BANDS.md")
VERIFIER = os.path.join(_HERE, "verify_bands_doc.py")
LEAF_CTL = os.path.join(_HERE, "bandsweep-far20-leaf-2-cpl.json")
COLLIDER = os.path.join(_HERE, "bandsweep-far20-zzcollide.json")

R2_VERDICT_112 = (
    "| `112MSDCF` | 79 | 1 | 30 | **3.012** PASS | **1.724** MARG | "
    "**1.202** FAIL | **1.089** FAIL | **1.049** FAIL | **0.20** |")
R2_VERDICT_PAPER = (
    "| `paper-sweep` | 62 | 1 | 30 | **22.551** PASS | **8.699** PASS | "
    "**3.203** PASS | **2.002** PASS | **2.066** PASS | **0.48** |")
R2_VERDICT_DRY = (
    "| `dry-erase-marker-head-cpl` | 300 | 4 | 24 | **117.666** PASS | "
    "**35.900** PASS | **9.665** PASS | **4.877** PASS | **6.647** PASS | "
    "**0.48** |")
R2_CI_TWEEZERS = (
    "| `tweezers-cpl` | 196.995 [157.975, 243.732] | 81.304 [61.367, 106.052] |")
R1_VERDICT_LEAF = (
    "| `leaf-2-cpl` | 182 | 2 | 30 | **2.218** PASS | 1.512 MARG | 1.171 FAIL | "
    "1.068 FAIL | 1.040 FAIL | **0.20** |")
BAND0_112 = "| `112MSDCF` | 1.202 | 1.089 | 1.049 | **NOISE** |"
LADDER_112 = "| `112MSDCF` | 0.20 | 0.20 | same |"

# (name, why it matters, old_line, new_line-or-None-to-delete)
ARMS = [
    ("R2-R-verdict-duplicated-elsewhere",
     "112MSDCF's 1.202 also appears in the §10 band-0 table, so a "
     "presence-in-whole-file check reads GREEN on this. This is the exact "
     "defect that made version 1 useless.",
     R2_VERDICT_112, R2_VERDICT_112.replace("**1.202** FAIL", "**1.212** FAIL")),

    ("R2-CI-hi",
     "a CI bound in a round-2 CI row; catches a transcription slip in the "
     "interval rather than the point estimate.",
     R2_CI_TWEEZERS, R2_CI_TWEEZERS.replace("106.052", "106.062")),

    ("R2-N-step-kept",
     "the sample-size cell, which is how a decimated sweep would be "
     "misreported as a full one.",
     R2_VERDICT_PAPER, R2_VERDICT_PAPER.replace("| 62 | 1 | 30 |",
                                                "| 62 | 1 | 31 |")),

    ("R1-R-verdict",
     "round 1 must still be covered after the loader was rewritten to glob.",
     R1_VERDICT_LEAF, R1_VERDICT_LEAF.replace("**2.218** PASS",
                                              "**2.228** PASS")),

    ("row-deleted",
     "a subject in the JSON with no verdict row must read UNRESOLVED, not "
     "pass by absence.",
     R2_VERDICT_DRY, None),

    ("row-duplicated",
     "two verdict rows for one subject is ambiguous; resolving to the first "
     "is how defect 1 survived, so it must refuse instead.",
     R2_VERDICT_DRY, R2_VERDICT_DRY + "\n" + R2_VERDICT_DRY),

    # ---- CONCLUSION FLIPS -------------------------------------------------
    # ORCH broadcast 2026-08-27: V-NEVERWORSE's verifier passed 712 green
    # checks on a document whose verdict had been flipped from "refuted" to
    # "confirmed", because it tested for the PRESENCE of a string.  A verifier
    # that certifies every NUMBER and no CONCLUSION certifies the wrong thing:
    # the numbers are the evidence, the verdict and the boundary are the
    # PRODUCT, and the product is what other lanes consume.  These four arms
    # leave every number this document reports intact and change only what it
    # CONCLUDES from them.
    ("conclusion-flip-band-verdict",
     "112MSDCF 0.25-0.30 FAIL -> PASS with R still 1.202. Flips a band from "
     "noise to signal and re-licenses the gate-floor arm this lane withdrew "
     "the licence from. Not one digit changes.",
     R2_VERDICT_112, R2_VERDICT_112.replace("**1.202** FAIL", "**1.202** PASS")),

    ("conclusion-flip-boundary",
     "112MSDCF boundary 0.20 -> 0.48. The boundary IS the headline of this "
     "document and the single value other lanes act on. Every R, CI and "
     "sample count stays correct.",
     R2_VERDICT_112, R2_VERDICT_112.replace("| **0.20** |", "| **0.48** |")),

    ("conclusion-flip-band0-NOISE-to-SIGNAL",
     "§10's band-0 verdict, which ORCH has adopted project-wide as the rule "
     "for whether a band-0 result is licensed at all.",
     BAND0_112, BAND0_112.replace("**NOISE**", "**SIGNAL**")),

    ("conclusion-flip-ladder-control",
     "the far-ladder CONTROL's own verdict: 'same' -> 'MOVED'. A flipped "
     "control result invalidates the measurement while every measured "
     "boundary in the row still reads 0.20.",
     LADDER_112, "| `112MSDCF` | 0.20 | 0.48 | MOVED |"),

    ("conclusion-flip-summary-claim",
     "§9.4's summary '6/6 unchanged' -> '5/6'. The summary is the sentence "
     "other lanes read instead of the table, so it must be certified against "
     "the rows rather than trusted. Anchored on the full sentence because "
     "§12 now quotes the bare token and the harness correctly refused it.",
     "**6/6 unchanged**, matching the 5/5 of",
     "**5/6 unchanged**, matching the 5/5 of"),

    ("band0-row-deleted",
     "a derived table silently losing a subject. A check that matches "
     "nothing prints the same green as one that matches, so the row COUNT is "
     "itself a check.",
     "| `bee-1-cpl` | 10.728 | 4.732 | 3.629 | SIGNAL |", None),
]


def run_verifier():
    p = subprocess.run([sys.executable, VERIFIER], capture_output=True,
                       text=True, cwd=_HERE)
    return p.returncode, (p.stdout + p.stderr)


def plant(text, old, new):
    n = text.count(old)
    if n != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND EXACTLY ONCE (count={n}).\n"
            f"  {old[:90]}...\n"
            "The arm would have measured nothing. Refusing to report a result.")
    return text.replace(old, "" if new is None else new, 1)


def main():
    original = open(DOC, encoding="utf-8").read()
    backup = os.path.join(tempfile.gettempdir(), "V-LINEAR-BANDS.commission.bak")
    shutil.copy2(DOC, backup)
    print(f"backup: {backup}\n")

    caught = missed = 0
    try:
        rc, out = run_verifier()
        print(f"[baseline    ] exit={rc}  (expect 0)")
        if rc != 0:
            print(out)
            raise SystemExit("BASELINE IS NOT GREEN -- commission the document "
                             "before commissioning the verifier.")

        for name, why, old, new in ARMS:
            mutated = plant(original, old, new)
            if mutated == original:
                raise SystemExit(f"{name}: mutation was a no-op.")
            open(DOC, "w", encoding="utf-8", newline="").write(mutated)
            rc, out = run_verifier()
            verdict = "CAUGHT" if rc != 0 else "MISSED"
            if rc != 0:
                caught += 1
            else:
                missed += 1
            print(f"[{verdict:6}      ] exit={rc}  {name}")
            print(f"                 why: {why}")
            if rc == 0:
                print("  ---- verifier output on the corrupted document ----")
                print(out)
            open(DOC, "w", encoding="utf-8", newline="").write(original)

        # Positive control on the LOADER, not the row checks: a second file
        # carrying genuinely DIFFERENT values for a subject already loaded must
        # be refused. The §6.1 control is real disagreeing data, so this is a
        # real collision rather than a synthetic one.
        shutil.copy2(LEAF_CTL, COLLIDER)
        try:
            rc, out = run_verifier()
            hit = rc != 0 and "AMBIGUOUS" in out
            if hit:
                caught += 1
            else:
                missed += 1
            print(f"[{'CAUGHT' if hit else 'MISSED':6}      ] exit={rc}  "
                  "loader-collision-disagreeing-values")
            print("                 why: two files disagreeing about one "
                  "subject must be refused, not silently first-wins.")
            if not hit:
                print(out)
        finally:
            os.remove(COLLIDER)
    finally:
        shutil.copy2(backup, DOC)

    rc, out = run_verifier()
    print(f"\n[restored    ] exit={rc}  (expect 0)")
    restored_ok = (rc == 0 and open(DOC, encoding="utf-8").read() == original)
    print(f"document byte-identical to pre-commission: "
          f"{open(DOC, encoding='utf-8').read() == original}")

    total = len(ARMS) + 1
    print(f"\n  caught : {caught}")
    print(f"  missed : {missed}")
    print(f"  -----------------")
    print(f"  arms   : {caught + missed}   (declared {total})")
    if caught + missed != total:
        print("  ARM COUNT MISMATCH -- an arm did not run.")
        return 1
    return 0 if (missed == 0 and restored_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
