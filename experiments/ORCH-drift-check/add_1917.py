"""Bank facts 1917-1920 from lane V-DILUTE's soft-gate reachability work.

Auto-detects the current tail and hard-errors if it is not the expected 1916,
because a lane has previously written fact rows out from under the orchestrator.
"""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1916

ROWS = [
    ("MEASURED", "V-DILUTE",
     "**A FIFTH CONTROL KNOB IS INERT: `STREHL_SOFT_GATE` MOVED NOTHING ON THE DEFAULT BACKEND, "
     "AND THE SAME VARIABLE MOVES 97 PERCENT OF THE PLANE ON A BACKEND NOBODY SHIPS.** On "
     "`109MSDCF` at N=22, `gaussian` versus unset differ on **0 of 24,724,512 samples**, while "
     "under `--merge estimator` the identical variable moves **23,980,319 of 24,724,512**. The "
     "measurement is commissioned three ways - determinism, sensitivity, specificity - and the "
     "predictions were committed at `4dca927d` **before any arm ran**. **Independently "
     "reproduced by V-KILLB0** on `bee-1-cpl` and `112MSDCF`, so this is not one lane's harness "
     "error. **TIME-STAMPED, AND THIS QUALIFIER IS LOAD-BEARING: this is the state BEFORE lane "
     "BUILD-SOFTGATE's `40307289`, whose entire purpose was to wire the soft kernel into the "
     "pyramid.** The row records what was true when measured, not necessarily what is true at "
     "HEAD; re-measure before quoting it forward. The count of knobs found inert this session is "
     "now five, and the fourth shipped a banner asserting the opposite - **an environment "
     "variable that validates its spelling has proven nothing about whether it reaches the "
     "code.**"),

    ("MEASURED", "V-DILUTE",
     "**COMPARING TWO GATE KERNELS AT THE SAME CALIBRATED TOLERANCE IS NOT A CONTROLLED "
     "COMPARISON, BECAUSE TOLERANCE AND EFFECTIVE WIDTH ARE NOT INDEPENDENT.** `Gate::tolerance()` "
     "is shared across kernels, and on `109MSDCF` that same T admits mean **n_eff 4.674 under "
     "the hard gate and 19.295 of 22 under the Gaussian**, with **79.2 percent of the plane at "
     "n_eff of 20 or more** - the soft kernel is averaging nearly the whole stack where the hard "
     "one averaged under five. Holding T fixed varies shape and width together, so any "
     "hard-versus-soft result reported at equal T has confounded the two. The repair is to "
     "match on effective width rather than on the threshold parameter. **Generalises beyond "
     "gates: a shared parameter name across two implementations is not a shared meaning, and "
     "equalising the name is not equalising the experiment.**"),

    ("MEASURED", "V-DILUTE",
     "**A CORRECTION KEYED ON AN INTEGER COUNT LOSES 99.4 PERCENT OF ITS REACH THE MOMENT THE "
     "COUNT STOPS BEING INTEGRAL.** `selection_inflation` keys on the admitted-frame count, but "
     "`fold_inner` skips only at weight not greater than zero and increments `n` afterwards, so "
     "under a soft kernel **`n` counts every frame that survives f32 underflow** rather than "
     "every frame that meaningfully contributed. Measured consequence: the population at n_eff "
     "of 1 or below - the population the correction exists to serve - **falls from 3.936 percent "
     "to 0.023 percent**. The correction is not disabled and raises no error; it simply stops "
     "finding anything to correct. **This is the arithmetic form of a silent scope collapse: the "
     "guard still runs, still returns, and still reports success on a domain that has been "
     "emptied underneath it.**"),

    ("MEASURED", "V-DILUTE",
     "**THE INTEGER-VERSUS-EFFECTIVE-COUNT CHOICE IS DOUBLY LATENT AND CANNOT MATTER TODAY BY "
     "EITHER ROUTE.** `SELECTION_INFLATION` is **1.0**, and **both branches of "
     "`selection_inflation` return 1.0**, so the branch is inert at the value level as well as "
     "the wiring level; making it live requires **both** fact 448's curve to be armed **and** "
     "the soft kernel to reach the pyramid. Recorded so that a future reader does not mistake "
     "the preceding row for a live defect and 'fix' a path that is switched off twice over. "
     "**The discipline it argues for: when a finding concerns a code path, state its reachability "
     "in the same breath as its magnitude, or the magnitude will be read as impact.**"),
]


def build_row(num, kind, lane, body):
    if "|" in body:
        raise SystemExit(f"fact {num}: raw pipe in body")
    if body.count("*") % 2 != 0:
        raise SystemExit(f"fact {num}: odd asterisk count")
    return f"| {num} | {kind} | {lane} | {body} |\n"


def main():
    with io.open(PATH, "r", encoding="utf-8", newline="") as fh:
        lines = fh.readlines()

    ids = [int(m.group(1)) for m in
           (re.match(r"^\|\s*(\d+)\s*\|", ln) for ln in lines) if m]
    tail = max(ids)
    if tail != EXPECTED_TAIL:
        raise SystemExit(
            f"tail is {tail}, expected {EXPECTED_TAIL} — another lane wrote rows; "
            "re-read SYNTHESIS before banking")

    anchor = f"| {tail} |"
    hits = [i for i, ln in enumerate(lines) if ln.startswith(anchor)]
    if len(hits) != 1:
        raise SystemExit(f"anchor matched {len(hits)} lines, expected exactly 1")
    at = hits[0]

    new = []
    for offset, (kind, lane, body) in enumerate(ROWS, start=1):
        num = tail + offset
        if any(ln.startswith(f"| {num} |") for ln in lines):
            raise SystemExit(f"fact {num} already present")
        new.append(build_row(num, kind, lane, body))

    lines[at + 1:at + 1] = new

    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)

    print(f"inserted {len(new)} rows ({tail + 1}-{tail + len(new)}) after fact {tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
