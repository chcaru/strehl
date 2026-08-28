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

# Section 13 anchors.  Each is a FULL row: anchoring on a fragment such as
# "1.079" would land on whichever occurrence came first, which is how the
# earlier `§2.7` mis-plant happened in a neighbouring lane and how a green
# negative control can be a statement about nothing.
S13_112 = ("| `112MSDCF` | 79 | 1.202 | **1.079** | [1.040, 1.121] | 1.102 | "
           "**FAIL (noise)** |")
S13_DRY = ("| `dry-erase-marker-head-cpl` | 300 | 9.665 | **4.530** | "
           "[3.115, 5.947] | 5.283 | **PASS** |")
S13_DELTA_112 = "| `112MSDCF` | 1.089 | 1.079 | \u22121.0% |"
S13_FARCTL = "| `--far 24` | 6 developed frames | **4.659** | **PASS** |"
S13_BEE = ("| `bee-1-cpl` | 299 | 10.728 | **5.311** | [3.083, 7.638] | "
           "4.047 | **PASS** |")
S13_DELTA_BEE = "| `bee-1-cpl` | 4.732 | 5.311 | +12.2% |"

# sec.9.1 halo-retraction anchors.  Both are full lines and both are unique;
# `plant()` refuses anything that does not occur exactly once, so a reflow of
# either paragraph fails loudly here rather than silently disarming an arm.
S9_HALO_NEG = ("step in a 22461 DN ramp. **No halo is demonstrated on any of "
               "the 26 masters.**")
S9_HALO_ROW = ("| `flat-on-ruler-cpl` | **selected** on a halo verdict (fact "
               "1841, overshoot +4481.8 DN) that has **since been retracted** "
               "\u2014 see the note below |")

# sec.14 grid anchors.  Full lines, each unique.
S14_BEE_ROW = ("| `bee-1-cpl` |" + " **PASS** |" * 14)
S14_CHIA_ROW = ("| `chia-seeds-cpl` |" + " -- |" * 14)
S14_COUNT = ("`--` = UNQUALIFIED (never measured). 22 of 34 corpus subjects "
             "have never been band-qualified at any slice.")
S14_EXIT3 = ("| 3 | `UNQUALIFIED` | no \u2014 **never measured**, a queue "
             "item, not a failure |")
S14_INTERP = ("confident guess easy. `paper-sweep` is PASS at 0.30\u20130.40 "
              "and **marg** at")
S2_CHECKS = ("`experiments/V-LINEAR/verify_bands_doc.py` (804 checks, "
             "cell-anchored, verdicts")
S2_ARMS = ("`commission_verify_doc.py` at 38 defect arms caught and 3 null "
           "arms quiet, and")

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

    # ---- SECTION 13: the 0.30-0.35 narrow-band measurement -----------------
    # This section exists because ORCH withdrew the licence from his own
    # broadcast figure on the strength of this lane's table.  It is therefore
    # the section most likely to be quoted and the one where a reversed
    # conclusion would do the most damage, so it gets conclusion-flip arms
    # before it gets anything else.
    ("s13-conclusion-flip-112-FAIL-to-PASS",
     "THE ARM THAT MATTERS. 112MSDCF 0.30-0.35 FAIL -> PASS with R still "
     "1.079 and the CI still [1.040, 1.121]. This single token decides "
     "whether ORCH's -44.6% is licensed. Every digit stays correct.",
     S13_112, S13_112.replace("**FAIL (noise)** |", "**PASS** |")),

    ("s13-conclusion-flip-gate-PASS-to-FAIL",
     "the GATE. dry-erase 0.30-0.35 PASS -> FAIL voids §13 entirely, because "
     "a FAIL there means the instrument cannot resolve a 0.05-wide band and "
     "112MSDCF's FAIL says nothing about 112MSDCF.",
     S13_DRY, S13_DRY.replace("**PASS** |", "**FAIL (noise)** |")),

    ("s13-R-narrow",
     "the point estimate the whole section turns on.",
     S13_112, S13_112.replace("**1.079**", "**1.179**")),

    ("s13-CI-upper",
     "the CI upper bound, which is what makes this a decisive FAIL rather "
     "than a marginal one.",
     S13_112, S13_112.replace("1.121]", "1.521]")),

    ("s13-delta-recomputed",
     "§13.7's delta is a CONCLUSION about how far the narrow band moved from "
     "the wide one; quoting it back would certify it against itself, so the "
     "verifier recomputes it from both records.",
     S13_DELTA_112, S13_DELTA_112.replace("−1.0%", "−9.0%")),

    ("s13-far-control-flipped",
     "§13.6's far-matched control is the only thing standing between "
     "coffee-bubbles' MARGINAL and a sampling artifact. Flipping its verdict "
     "leaves the confound uncontrolled.",
     S13_FARCTL, S13_FARCTL.replace("**PASS** |", "**FAIL (noise)** |")),

    ("s13-commissioning-not-zero",
     "the RNG commissioning claim. If a pre-existing band DID move, every "
     "committed number in this document is suspect, so '0 of 12' must be "
     "certified against the records rather than typed.",
     "| `paper-sweep` | 0 of 12 | exact zero |",
     "| `paper-sweep` | 1 of 12 | exact zero |"),

    ("s13-arithmetic-claim",
     "§13.5's 'how far below the bar' figure, which is the sentence a reader "
     "takes away instead of the interval.",
     "**0.379 below the MARGINAL bar**", "**0.079 below the MARGINAL bar**"),

    ("s13-exclusion-sentence-deleted",
     "the documented exclusion of coffee-bubbles. Deleting it makes the "
     "verifier's loader silently disagree with the prose -- a subject dropped "
     "from the canonical tables with nothing saying so. This is the arm for "
     "'do not silently drop an awkward one'.",
     "`coffee-bubbles` is **deliberately excluded from the canonical "
     "eleven-subject", None),

    ("s13-row-deleted",
     "a §13.4 row vanishing. The row count is the only thing that "
     "distinguishes five subjects measured from four measured and one "
     "forgotten.",
     S13_DRY, None),

    # ---- 13.9: bee-1-cpl, the subject ORCH routed another lane onto --------
    ("s13-conclusion-flip-bee-PASS-to-FAIL",
     "bee-1-cpl 0.30-0.35 PASS -> FAIL. ORCH has directed the pyramid lane to "
     "score the confidence exponent at depth on THIS subject at THIS slice, so "
     "this token decides whether that lane is measuring signal or grain. R "
     "stays 5.311 and the CI stays [3.083, 7.638].",
     S13_BEE, S13_BEE.replace("**PASS** |", "**FAIL (noise)** |")),

    ("s13-bee-R",
     "bee's point estimate, quoted from the re-developed record rather than "
     "the canonical one, so this also covers the record-selection logic.",
     S13_BEE, S13_BEE.replace("**5.311**", "**3.311**")),

    ("s13-bee-delta-sign",
     "bee is the only subject whose narrow band reads HIGHER than its wide "
     "one, which is what shows narrowing is not a systematic penalty. "
     "Flipping the sign inverts that conclusion while leaving both R values "
     "correct.",
     S13_DELTA_BEE, S13_DELTA_BEE.replace("+12.2%", "\u221212.2%")),

    # ---- sec.9.1 halo retraction (V-REVIEW's finding, cited by this lane) ----
    #
    # These three are the reason the retraction is worth checking at all.  Not
    # one of them changes a number: every R, CI and verdict in the document
    # stays correct under all three.  What they change is what a reader
    # believes about four subjects and about an instrument another lane has
    # withdrawn.  A verifier that only certifies evidence sails through all of
    # them -- which is precisely the failure sec.12.3 documents six times.
    ("s91-halo-negation-reversed",
     "flips the retraction back to an assertion: 'No halo is demonstrated' -> "
     "'A halo is demonstrated'. Every number in the document remains correct. "
     "This is the conclusion-reversal shape, and it re-asserts a premise "
     "V-REVIEW has measured to be an artifact.",
     S9_HALO_NEG,
     S9_HALO_NEG.replace("**No halo is demonstrated",
                         "**A halo is demonstrated")),

    ("s91-halo-negation-deleted",
     "DELETION rather than reversal, per ORCH's third lesson -- deleting a "
     "finding is cheaper than stating it wrongly, and a document that simply "
     "goes quiet about the retraction leaves the four selection rows as the "
     "only thing a scanning reader sees.",
     S9_HALO_NEG, "step in a 22461 DN ramp."),

    ("s91-halo-selection-row-restored",
     "restores the ORIGINAL pre-retraction wording of one selection row. The "
     "sentence three paragraphs below still says the verdicts were retracted, "
     "so the document contradicts itself and a whole-file presence test for "
     "the retraction still passes. Only a per-row check catches this.",
     S9_HALO_ROW,
     "| `flat-on-ruler-cpl` | fails the halo measurement (fact 1841, "
     "overshoot **+4481.8 DN**) |"),

    # ---- sec.14, the licence grid ---------------------------------------
    # 484 of the verifier's checks are grid cells. Before these arms existed,
    # every one of them was uncommissioned: a grid that agreed with a broken
    # loader would have read exactly as green as a correct one.
    ("s14-measured-cell-flipped",
     "flips one measured grid cell from PASS to FAIL. Nothing else in the "
     "document changes, and every R and CI stays correct. A lane reading the "
     "grid would refuse a licence it actually holds.",
     S14_BEE_ROW, S14_BEE_ROW.replace("| **PASS** |", "| FAIL |", 1)),

    ("s14-measured-cell-blanked",
     "claims UNQUALIFIED for a cell that IS measured. This is the softer half "
     "of the section's whole point -- it turns an answer back into a queue "
     "item and would have someone re-spend a develop that was already paid.",
     S14_BEE_ROW, S14_BEE_ROW.replace("| **PASS** |", "| -- |", 1)),

    ("s14-unmeasured-cell-claimed-PASS",
     "THE MOST DANGEROUS ONE: licenses a cell nobody has ever measured. "
     "`chia-seeds-cpl` has no record at any slice; this row would tell a lane "
     "it is qualified. It is the exact inversion of the distinction sec.14 "
     "exists to preserve, and no number anywhere else in the document moves.",
     S14_CHIA_ROW, S14_CHIA_ROW.replace("| -- |", "| **PASS** |", 1)),

    ("s14-unqualified-count-wrong",
     "the summary count of unmeasured subjects. If it drifts low, the corpus "
     "looks better covered than it is -- which is the impression the whole "
     "section is built to prevent.",
     S14_COUNT, S14_COUNT.replace("22 of 34", "21 of 34")),

    ("s14-exit-code-table-wrong",
     "changes the documented exit code for UNQUALIFIED from 3 to 2. Other "
     "lanes are wiring `bandq.py` into their own gates FROM THIS TABLE, so a "
     "wrong code here makes the document lie to every one of them. Checked "
     "against bandq.py's actual constants, not against itself.",
     S14_EXIT3, S14_EXIT3.replace("| 3 |", "| 2 |")),

    ("s14-unqualified-reads-as-a-licence",
     "flips the licence column on the UNQUALIFIED row from `no` to `yes`. No "
     "exit code moves, no number moves, the table still has six well-formed "
     "rows -- and it now tells every lane that a subject nobody ever measured "
     "is licensed. That is the single sentence this section exists to prevent "
     "and it is the error the orchestrator made twice.",
     S14_EXIT3, S14_EXIT3.replace("| no \u2014", "| yes \u2014")),

    ("s14-anti-interpolation-example-inverted",
     "inverts the one concrete piece of evidence sec.14.9 offers for refusing "
     "to interpolate. Both verdicts named are real, both slices are real, and "
     "the sentence still reads perfectly -- it just now argues the opposite. "
     "The records-based check alone did NOT catch this; it needed a check "
     "pinned to the claim.",
     S14_INTERP,
     "confident guess easy. `paper-sweep` is PASS at 0.30\u20130.35 "
     "and **marg** at"),

    # ---- the document's claims about its own instruments -----------------
    # Both of these were LIVE, not hypothetical: the document still claimed
    # 310 checks and 29 arms after sec.14 had moved them to 804 and 36.
    ("s2-check-count-stale",
     "understates how many checks this document passes. A stale instrument "
     "count misrepresents how hard the document's own claims have been pushed "
     "on, in the lane's favour, and nothing else in the file changes.",
     S2_CHECKS, S2_CHECKS.replace("804 checks", "799 checks")),

    ("s2-arm-count-stale",
     "reverts the commissioning arm count to its pre-sec.14 value. This is "
     "the exact stale figure that was live in this file until the pin was "
     "added -- the document claiming 29 arms while the harness ran 36.",
     S2_ARMS, S2_ARMS.replace("38 defect arms", "29 defect arms")),
]

# ---- SPECIFICITY (null) arms ------------------------------------------------
# ORCH broadcast 2026-08-27: "Commissioning sensitivity is not commissioning
# specificity. Planting a signal and confirming detection says nothing about
# whether noise is rejected. Plant noise too."
#
# Every arm above is a defect that MUST be caught.  Nothing above distinguishes
# a verifier that detects reversed conclusions from one that exits non-zero on
# ANY edit whatsoever -- both score 26/26.  An indiscriminate verifier is
# useless in the more dangerous direction, because a lane would learn to ignore
# its RED.
#
# The loader-collision arm below is run inline rather than declared in ARMS
# (it mutates the data directory, not the document), so the harness's true
# defect-arm count is ARMS + 1.  It is named once, here, because the document
# quotes it and verify_bands_doc.py pins the document to it.
TOTAL_ARMS_EXTRA = 1
#
# These edits change the document's prose without touching a single checked
# claim.  The verifier MUST stay GREEN on all of them.
NULLS = [
    ("null-prose-reworded",
     "a sentence rewritten with identical meaning and no number in it.",
     "ORCH authorised measuring 0.30–0.35 specifically. This section is that",
     "ORCH authorised measuring 0.30–0.35 specifically. This section reports that"),

    ("null-prose-deleted",
     "DELETION of an unchecked sentence. Deletion arms above are all of "
     "checked rows; this shows deletion per se is not what trips the "
     "verifier, so those CAUGHT results mean what they claim.",
     "It is not void. On the strongest qualifier:\n\n", ""),

    ("null-sentence-added",
     "new prose asserting nothing the verifier certifies. A verifier that "
     "reddens on added text would make the document unmaintainable.",
     "That is a statement about the measurement, not about the",
     "That is a statement about the measurement and not about the"),
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
    nulls_ok = nulls_bad = 0
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

        # ---- specificity: these MUST stay green -------------------------
        for name, why, old, new in NULLS:
            mutated = plant(original, old, new)
            if mutated == original:
                raise SystemExit(f"{name}: null mutation was a no-op.")
            open(DOC, "w", encoding="utf-8", newline="").write(mutated)
            rc, out = run_verifier()
            quiet = (rc == 0)
            if quiet:
                nulls_ok += 1
            else:
                nulls_bad += 1
            print(f"[{'quiet' if quiet else 'FALSE-ALARM':11}  ] exit={rc}  "
                  f"{name}")
            print(f"                 why: {why}")
            if not quiet:
                print("  ---- verifier reddened on a harmless edit ----")
                print(out)
            open(DOC, "w", encoding="utf-8", newline="").write(original)
    finally:
        shutil.copy2(backup, DOC)

    rc, out = run_verifier()
    print(f"\n[restored    ] exit={rc}  (expect 0)")
    restored_ok = (rc == 0 and open(DOC, encoding="utf-8").read() == original)
    print(f"document byte-identical to pre-commission: "
          f"{open(DOC, encoding='utf-8').read() == original}")

    total = len(ARMS) + TOTAL_ARMS_EXTRA
    print(f"\n  caught      : {caught}")
    print(f"  missed      : {missed}")
    print(f"  -----------------")
    print(f"  defect arms : {caught + missed}   (declared {total})")
    print(f"\n  quiet       : {nulls_ok}")
    print(f"  FALSE ALARM : {nulls_bad}")
    print(f"  -----------------")
    print(f"  null arms   : {nulls_ok + nulls_bad}   (declared {len(NULLS)})")
    if caught + missed != total:
        print("  ARM COUNT MISMATCH -- an arm did not run.")
        return 1
    if nulls_ok + nulls_bad != len(NULLS):
        print("  NULL COUNT MISMATCH -- a null arm did not run.")
        return 1
    if nulls_bad:
        print("  SPECIFICITY FAILURE -- the verifier reddens on edits that "
              "change no checked claim, so its RED carries no information.")
    return 0 if (missed == 0 and nulls_bad == 0 and restored_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
