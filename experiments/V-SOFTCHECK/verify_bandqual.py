"""verify_bandqual.py -- report verifier for docs/research/V-SOFTCHECK-bandqual.md.

WHY THIS REPLACES vblob.py / vblob2.py
--------------------------------------
Those tested for the PRESENCE of strings and were commissioned with a last-digit
mutation (1.5525 -> 1.5526). ORCH propagated V-NEVERWORSE's finding that a presence
test cannot detect a REVERSED CONCLUSION: their verifier passed 712 green checks while
a section's verdict was flipped from "refuted" to "confirmed".

I tested my own verifiers for that shape rather than assuming they were exempt. They
were not. Three of six conclusion flips passed GREEN with EVERY NUMBER INTACT:

    M1 headline reversed        PARTIAL WITHDRAWAL -> FULLY CONFIRMED, NOTHING WITHDRAWN
    M2 sec.4 un-withdrawn       "are withdrawn as resolution" -> "are RETAINED as"
    M5 sec.3c.1 un-withdrawn    "That is withdrawn." -> "That is confirmed."

So this document's entire verdict could be reversed and my old verifier reported 26/26.

WHAT IS DIFFERENT HERE
----------------------
1. Every CLAIM is named and pinned to its own anchor, so a failure says WHICH conclusion
   moved rather than "an anchor fell".
2. Commissioning requires each mutation to be caught BY THE CLAIM IT TARGETS. A mutation
   caught by some other check is recorded as MIS-ATTRIBUTED, not as a pass -- otherwise
   one over-broad anchor masks the absence of a specific one.
3. The battery flips CONCLUSIONS with all numbers held intact, and separately perturbs a
   number, so both failure directions are commissioned (project discipline: plant a defect
   in both directions before trusting an instrument).
4. Any mutation whose target string is absent is a HARD ERROR, never a silent pass.
"""
import re, subprocess, sys

REPO = r"C:\dev\blog\death-of-software\projects\strehl"
DOC  = "docs/research/V-SOFTCHECK-bandqual.md"

def blob(rev, path):
    r = subprocess.run(["git", "show", "%s:%s" % (rev, path)], capture_output=True, cwd=REPO)
    if r.returncode:
        sys.exit("git show failed: " + r.stderr.decode("utf-8", "replace"))
    return r.stdout.decode("utf-8")          # bytes, never a shell redirect

def norm(t):
    t = re.sub(r"(?m)^\s*>\s?", "", t)       # blockquote markers are not whitespace
    return re.sub(r"\s+", " ", t)

# claim id -> (what it certifies, anchor that must be present)
CLAIMS = {
 "VERDICT":      ("the document's headline verdict is a partial withdrawal",
                  "**Verdict: PARTIAL WITHDRAWAL.**"),
 "WITHDRAW-S4":  ("section 4 withdraws the 17.8%/18.8% numbers as resolution claims",
                  "-- 17.8% and 18.8% softer -- are withdrawn as resolution"),
 "WITHDRAW-F4":  ("finding 4 of the N-invariance doc is withdrawn entirely",
                  "**Also withdrawn, and this one dies hardest.**"),
 "WITHDRAW-XS":  ("my own cross-subject corroboration is withdrawn",
                  "**That is withdrawn.** The 2.419 is `113MSDCF`'s number specifically"),
 "DECLINE":      ("I decline the reinstatement V-LINEAR's bee boundary offers",
                  "I decline the reinstatement this offers me"),
 "NOMOVE":       ("correction #4 does not move my numbers",
                  "**My numbers do not move.**"),
 "BOUND-113":    ("113MSDCF boundary agrees exactly with V-LINEAR",
                  "| `113MSDCF` | **0.25** | **0.25** | **exact** |"),
 "BOUND-BEE":    ("bee boundary DISAGREES and mine is the conservative one",
                  "| `bee-1-cpl` | 0.48 | 0.30 | **no** -- mine is more conservative |"),
 "R-113":        ("113MSDCF operating-band R and CI",
                  "| 113MSDCF | 0.30-0.35 | 1.5525 | [1.4583,1.6437] | MARGINAL | carries real detail |"),
 "R-BEE":        ("bee operating-band R and CI",
                  "| bee-1-cpl | 0.30-0.35 | 1.8480 | [1.6403,2.0347] | MARGINAL | carries real detail |"),
 "ATTR-NOISE":   ("the 1.3 boundary is attributed to noisefloor.py",
                  "`experiments/V-LINEAR/noisefloor.py:93`"),
 "ATTR-BAND":    ("the 2.0 bar is attributed to bandsignal.py / V-LINEAR2 prereg",
                  "`experiments/V-LINEAR2/bandsignal.py:94-99` and `V-LINEAR2/PREREGISTRATION.md` sec.2"),
 "NOTBORROWED":  ("my 2.0 bar was pre-registered, not borrowed",
                  "arrived at before I had read either file"),
 "DEVELOP":      ("the noise-region label does not transfer to my develop path",
                  "false of this lane's `--srgb` merged masters"),
 "HYPOTHESIS":   ("the bee defocus-distance explanation is flagged as hypothesis",
                  "stated as a hypothesis and not a\nresult"),
 "RAWPOWER":     ("the noise-inflation guard is answered, not dodged",
                  "no\nsingle number in this document can be trusted on its own in a flat region"),
 "PREMIUM":      ("the flat stratum independently shows the selection premium",
                  "**Every FLAT entry is negative on both subjects: the deeper arm holds MORE flat-region\npower at every band**"),
 "LOWERBOUND":   ("the premium biases AGAINST the finding, so deficits are lower bounds",
                  "**the surviving\ndeficits in section 5 are lower bounds, not point estimates.**"),
 "UNSETTLED":    ("blur vs noise-policy remains unseparated within the textured stratum",
                  "I\nstill cannot separate blur from a noise-policy difference"),
}

# each mutation flips a CONCLUSION (numbers intact) and must be caught BY ITS OWN CLAIM
MUTATIONS = [
 ("VERDICT",     "**Verdict: PARTIAL WITHDRAWAL.**", "**Verdict: FULLY CONFIRMED, NOTHING WITHDRAWN.**"),
 ("WITHDRAW-S4", "are withdrawn as resolution", "are RETAINED as resolution"),
 ("WITHDRAW-F4", "**Also withdrawn, and this one dies hardest.**", "**Also confirmed, and this one stands hardest.**"),
 ("WITHDRAW-XS", "**That is withdrawn.**", "**That is confirmed.**"),
 ("DECLINE",     "I decline the reinstatement this offers me", "I accept the reinstatement this offers me"),
 ("NOMOVE",      "**My numbers do not move.**", "**My numbers move substantially.**"),
 ("BOUND-BEE",   "**no** -- mine is more conservative", "**yes** -- the instruments agree"),
 ("BOUND-113",   "| `113MSDCF` | **0.25** | **0.25** | **exact** |", "| `113MSDCF` | **0.25** | **0.25** | **none** |"),
 ("DEVELOP",     "false of this lane's `--srgb` merged masters", "true of this lane's `--srgb` merged masters"),
 ("HYPOTHESIS",  "stated as a hypothesis and not a\nresult", "stated as a measured result and not a\nhypothesis"),
 ("R-113",       "1.5525 | [1.4583,1.6437]", "1.5526 | [1.4583,1.6437]"),   # number direction
 ("RAWPOWER",    "no single number in this document can be trusted on its own in a flat region",
                 "every number in this document is trustworthy in a flat region"),
 ("PREMIUM",     "the deeper arm holds MORE flat-region power at every band",
                 "the deeper arm holds LESS flat-region power at every band"),
 ("LOWERBOUND",  "are lower bounds, not point estimates",
                 "are upper bounds, not point estimates"),
 ("UNSETTLED",   "I still cannot separate blur from a noise-policy difference",
                 "I have now separated blur from a noise-policy difference"),
]

def mutate(text, old, new):
    """Apply a mutation across wrapped prose.

    A literal str.replace fails on any phrase that spans a line break, and a mutation
    that does not land is an instrument measuring nothing -- so this joins tokens on
    \\s+ and HARD-ERRORS if the pattern is absent. (A lambda supplies the replacement so
    backslashes in `new` are never read as backreferences.)
    """
    pat = re.compile(r"\s+".join(re.escape(t) for t in old.split()))
    if not pat.search(text):
        sys.exit("MUTATION TARGET NOT FOUND (verifier is measuring nothing): %r" % old[:70])
    return pat.sub(lambda m: new, text)

def failing(txt):
    n = norm(txt)
    return [k for k, (_, a) in CLAIMS.items() if norm(a) not in n]

def main():
    doc = blob("HEAD", DOC)
    base = failing(doc)
    print("=== CHECK: HEAD blob of %s ===" % DOC)
    for k, (what, _) in CLAIMS.items():
        print("  %-13s %-4s %s" % (k, "MISS" if k in base else "ok", what))
    print("  ---> %d/%d claims certified\n" % (len(CLAIMS) - len(base), len(CLAIMS)))

    print("=== COMMISSIONING: every mutation must be caught by ITS OWN claim ===")
    caught = mis = silent = 0
    for claim, old, new in MUTATIONS:
        mut = mutate(doc, old, new)
        nums_same = re.findall(r"\d+\.\d+", doc) == re.findall(r"\d+\.\d+", mut)
        f = failing(mut)
        if claim in f:
            caught += 1; verdict = "RED (by %s)" % claim
        elif f:
            mis += 1;    verdict = "MIS-ATTRIBUTED (caught by %s)" % ",".join(f)
        else:
            silent += 1; verdict = "*** GREEN -- CONCLUSION REVERSED, VERIFIER SILENT ***"
        print("  %-13s numbers %-7s %s" % (claim, "intact" if nums_same else "changed", verdict))
    tot = len(MUTATIONS)
    print("\n  caught %d + mis-attributed %d + silent %d = %d mutations" % (caught, mis, silent, tot))
    ok = (not base) and caught == tot
    print("\nVERDICT: %s" % ("GREEN -- document certified, verifier commissioned"
          if ok else "RED -- see above"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
