"""Bank facts 1874-1878 from V-KILLB0's channel audit, V-ORACLE and V-SPEED."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1873 | MEASURED | ORCH |"

ROWS = [
    ("1874", "MEASURED", "V-KILLB0",
     "**A HARNESS CAN HAVE NO PASS/FAIL CHANNEL AT ALL AND STILL LOOK LIKE A PASSING TEST: "
     "`verdict.py` PRINTED THE WORD FAIL AND EXITED 0.** Audited through its real entry point "
     "with 8 arms: null, 3 reversals, 2 deletions, 2 specificity. Every designed outcome exited "
     "0. A search for any exit, raise or assert on its shipped path returned NONE, so the harness "
     "could not signal failure to a caller by any mechanism, and any CI step or LASTEXITCODE "
     "wrapper read it as green unconditionally. The `rev_defence` arm is the sharpest form: it "
     "printed `5/7 conclusion-flip arms caught  FAIL - the check is decorative` and returned "
     "success. Deleting arm A7 printed `6/6 ... PASS`, confirming that `caught == len(ARMS)` is "
     "satisfied by deletion. One arm exited 1 and the auditor REFUSED to score it as a detection, "
     "because it was an unhandled KeyError from an inconsistent mutation rather than a signal, "
     "and a consistent row deletion would have exited 0 silently."),

    ("1875", "MEASURED", "V-KILLB0",
     "**THE GATE-FLOOR REFUTED VERDICT SURVIVES ITS OWN HARNESS BEING BROKEN, BECAUSE THE DEFECT "
     "WAS IN THE REPORTING CHANNEL AND NOT IN THE DERIVATION.** Sensitivity 5 of 5: every "
     "reversal and deletion arm visibly moved the PRINTED conclusion, `rev_obs` and "
     "`rev_boundary` both collapsing REFUTED to NOT REFUTED with damaged bands going 5 to 0, and "
     "`rev_defence` correctly flipping the defence flag to False. Specificity 2 of 2: a "
     "prose-only edit and a perturbation of a subject with no `obs_struct` row both left the "
     "verdict untouched, so it is not hypersensitive. So `derive()` genuinely re-computes from "
     "the stored numbers and the five leaf-2-cpl bands are convicted on arithmetic. What was "
     "never true is the ASSURANCE the printed 7/7 implied. Generalisation: reading a harness's "
     "printed conclusion under mutation is evidence; trusting its exit code is not, until the "
     "channel itself has been commissioned. ORCH added the channel, since the author had just "
     "proved the file broken and should not certify its own repair, and commissioned it 4 of 4: "
     "deletion, silent rename and a neutered arm all exit 1, unmutated exits 0, file restored "
     "byte-identical."),

    ("1876", "MEASURED", "V-ORACLE",
     "**`flowers-cpl`'s REGIONAL BLUR IS A CAPTURE GAP, NOT A MERGE DEFECT: VERDICT (a) AT ALL "
     "SIX SITES ON LICENSED BANDS 2 AND 3.** This closes the last undiagnosed visual complaint "
     "against the shipping masters. Measured on pyramid masters only, which is what ships. "
     "Residual thread: GAP 1, site 1's 0.999 tie, is the one reading that could pull the verdict "
     "apart and is named rather than buried. Consequence for the product: the fix is a capture "
     "instruction, not a code change, which is exactly the case the reshoot advisor exists to "
     "serve."),

    ("1877", "MEASURED", "V-ORACLE",
     "**A SOURCE-VERSUS-MERGE RATIO IS SYSTEMATICALLY FLATTERED BY ANYTHING THAT ADDS SPURIOUS "
     "STRUCTURE TO THE MERGED IMAGE, AND TWO SEPARATE PRODUCT DEFECTS PUSH IT THE SAME WAY.** "
     "Excess light around edges inflates the merge arm, which drives the source-over-merge ratio "
     "down, which reads as capture-gap. The lateral-CA over-correction does this and had to be "
     "controlled for explicitly; the estimator's aura would do it again with the same sign. The "
     "published numbers are pyramid-only and clean of the second, but the vulnerability is "
     "structural to the statistic rather than incidental to one run, and it is the first thing "
     "to check on any future arm of it."),

    ("1878", "MEASURED", "V-SPEED",
     "**A NULL CONTROL THAT NEVER EXERCISES THE READ PATH CANNOT TELL A TINY EFFECT FROM A DEAD "
     "KNOB; THE LOAD-BEARING ARM IS THE ONE REQUIRED NOT TO MOVE.** `STREHL_HULL` measures aura "
     "1260.3 DN unset, 1260.3 DN on `inputrange`, 1263.3 DN on `perlevel`, 1298.8 DN unclamped. "
     "`hull_default()` returns `Hull::InputRange` when the variable is unset, so the `inputrange` "
     "arm exercises the environment read while being REQUIRED to match the unset arm exactly. "
     "Without it, a knob whose true effect is 1.2 DN of rim spread is indistinguishable from one "
     "never read at all, because both read zero at one decimal place. Verdict is therefore "
     "REACHABLE WITH A TINY EFFECT, not dead, and those have opposite consequences for whether "
     "the code stays: 30 `Hull::` sites are structurally consumed in `pyramid.rs`, the shipping "
     "backend, unlike `active_kernel()`. Two further notes recorded as landmines: a blanket "
     "find-and-replace on a verdict word acts on the token and not the claim, which is the same "
     "error family as a presence test; and `experiments/V-ORACLE/stageB.py:94` contains 28.5 as a "
     "Rec.709 red-plus-blue luma weight, a live figure that will collide with any grep hunting "
     "the retracted 28.5x aura multiplier."),
]


def build_row(num, status, source, body):
    if "|" in body:
        raise SystemExit("REFUSED: raw pipe in fact %s truncates the table row" % num)
    if body.count("*") % 2 != 0:
        raise SystemExit("REFUSED: odd asterisk count in fact %s leaves italics open" % num)
    return "| %s | %s | %s | %s |" % (num, status, source, body)


def main():
    with io.open(PATH, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)

    hits = [i for i, ln in enumerate(lines) if ln.startswith(ANCHOR_PREFIX)]
    if len(hits) != 1:
        raise SystemExit("REFUSED: anchor %r matched %d rows, expected 1"
                         % (ANCHOR_PREFIX, len(hits)))
    at = hits[0]
    for num, _s, _src, _b in ROWS:
        if any(ln.startswith("| %s |" % num) for ln in lines):
            raise SystemExit("REFUSED: fact %s already present" % num)

    new_rows = [build_row(*r) for r in ROWS]
    lines[at + 1: at + 1] = new_rows
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(newline.join(lines))
    print("inserted %d rows after fact 1873 (line %d)" % (len(new_rows), at + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
