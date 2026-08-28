"""concflip.py -- PRESERVED EVIDENCE for a reported defect in my own tooling.

This is the audit that found V-SOFTCHECK's ORIGINAL verifiers (vblob.py / vblob2.py,
scratch-only, now deleted) blind to a reversed conclusion. It is kept because it produced
a number I reported to the orchestrator, and deleting the instrument behind a reported
finding would leave the claim unsupported.

MEASURED, on the union of those two verifiers' 26 anchors, with EVERY NUMBER LEFT INTACT:

    M1 headline reversed        PARTIAL WITHDRAWAL -> FULLY CONFIRMED   *GREEN*
    M2 sec.4 un-withdrawn       "are withdrawn"    -> "are RETAINED"    *GREEN*
    M3 accept reinstatement                                             RED
    M4 boundary agree flipped                                           RED
    M5 sec.3c.1 un-withdrawn    "That is withdrawn"-> "That is confirmed" *GREEN*
    M6 numbers do move                                                  RED
    NUM last-digit (my old control, the ONLY kind I had used)           RED

    3 of 6 conclusion flips passed with every number correct.

So this document's entire verdict could have been reversed while the verifier reported
26/26 green. The old commissioning mutations were 1.5525->1.5526 and 2.3180->2.3181 --
both NUMBERS, which is exactly the shape that cannot detect a reversed conclusion.

SUPERSEDED BY verify_bandqual.py (claims pinned individually, VACUOUS detection) and
commission_entry.py (deletion + specificity arms driven through the shipped entry point).
Those are the live instruments. This one is history, and it will not run now that the
verifiers it audits are gone -- it is retained as the record of a measurement, not as a
tool. Its anchor lists below are the ones vblob.py/vblob2.py actually used.
"""
import re, subprocess, sys
def blob(p):
    r = subprocess.run(["git","show","HEAD:"+p], capture_output=True,
                       cwd=r"C:\dev\blog\death-of-software\projects\strehl")
    if r.returncode: sys.exit("git show failed")
    return r.stdout.decode("utf-8")
def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"(?m)^\s*>\s?", "", t))

A1 = ["NOISE-DOMINATED if r < 1.3 else carries real detail",
 "PASS if r >= 2.0 and CI low >= 1.5; MARGINAL if r >= 1.3; else FAIL(noise)",
 "`experiments/V-LINEAR/noisefloor.py:93`",
 "`experiments/V-LINEAR2/bandsignal.py:94-99` and `V-LINEAR2/PREREGISTRATION.md` sec.2",
 "The correction does not move my verdict, and my bar was not borrowed.",
 "arrived at before I had read either file",
 "| 113MSDCF | 0.30-0.35 | 1.5525 | [1.4583,1.6437] | MARGINAL | carries real detail |",
 "| bee-1-cpl | 0.30-0.35 | 1.8480 | [1.6403,2.0347] | MARGINAL | carries real detail |",
 "false of this lane's `--srgb` merged masters", "both CIs exclude 1.3",
 "the comparison band is the HIGHEST-frequency PASSing band",
 "**0.20-0.25 for `113MSDCF`** and **0.25-0.30 for `bee-1-cpl`**",
 "chosen before I had read that rule"]
A2 = ["| `113MSDCF` | **0.25** | **0.25** | **exact** |",
 "| `bee-1-cpl` | 0.48 | 0.30 | **no** -- mine is more conservative |",
 "| 0.20-0.25 | 2.419 [1.970,3.058] | 3.3235 [2.9495,3.9073] | PASS | PASS |",
 "**My numbers do not move.**", "never used a fixed corpus band",
 "`113MSDCF` 0.20-0.25 (2.419 and 3.3235) and\n`bee-1-cpl` 0.25-0.30 (10.728 and 2.3180)",
 "I decline the reinstatement this offers me", "boundary-\nshopping after seeing the data",
 "A cross-subject comparison of mine, withdrawn",
 "V-LINEAR's actual `bee-1-cpl` value at 0.20-0.25 is **27.993**, not\n2.419",
 "disagree there by 5.7x", "stated as a hypothesis and not a\nresult",
 "spanning **4.36x** across `far` in {8, 20, auto=50}"]
ANCH = A1 + A2

MUT = [
 ("M1 headline reversed",      "**Verdict: PARTIAL WITHDRAWAL.**", "**Verdict: FULLY CONFIRMED, NOTHING WITHDRAWN.**"),
 ("M2 sec.4 un-withdrawn",     "are withdrawn as resolution",      "are RETAINED as resolution"),
 ("M3 accept reinstatement",   "I decline the reinstatement this offers me", "I accept the reinstatement this offers me"),
 ("M4 boundary agree flipped", "| `bee-1-cpl` | 0.48 | 0.30 | **no** -- mine is more conservative |",
                               "| `bee-1-cpl` | 0.48 | 0.30 | **yes** -- the instruments agree |"),
 ("M5 sec.3c.1 un-withdrawn",  "**That is withdrawn.**",           "**That is confirmed.**"),
 ("M6 numbers do move",        "**My numbers do not move.**",       "**My numbers move substantially.**"),
 ("NUM last-digit (my old control)", "1.5525", "1.5526"),
]
doc = blob("docs/research/V-SOFTCHECK-bandqual.md")
base_missing = [a for a in ANCH if norm(a) not in norm(doc)]
print("baseline: %d/%d anchors present  %s\n" % (len(ANCH)-len(base_missing), len(ANCH),
      "OK" if not base_missing else "PROBLEM"))
print("%-34s %-9s %-7s %s" % ("mutation", "numbers", "caught", "detail"))
bad = []
for name, old, new in MUT:
    if doc.count(old) < 1:
        sys.exit("MUTATION TARGET NOT FOUND: %r" % old[:60])
    mut = doc.replace(old, new)
    nums_before = re.findall(r"\d+\.\d+", doc); nums_after = re.findall(r"\d+\.\d+", mut)
    intact = "INTACT" if nums_before == nums_after else "changed"
    miss = [a for a in ANCH if norm(a) not in norm(mut)]
    caught = bool(miss)
    if intact == "INTACT" and not caught: bad.append(name)
    print("%-34s %-9s %-7s %s" % (name, intact, "RED" if caught else "*GREEN*",
          ("%d anchor(s) fell" % len(miss)) if caught else "CONCLUSION REVERSED, VERIFIER SILENT"))
print()
if bad:
    print("DEFECT IN MY VERIFIER: %d conclusion-flip(s) passed with every number intact:" % len(bad))
    for b in bad: print("   - " + b)
    sys.exit(1)
print("verifier detects every conclusion flip tested")

