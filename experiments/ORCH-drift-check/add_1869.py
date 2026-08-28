"""Bank facts 1869-1872 from V-KILLB0's wind-down. Same anchor discipline as add_1865.py."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1868 | MEASURED | ORCH |"

ROWS = [
    ("1869", "MEASURED", "V-KILLB0",
     "**`STREHL_SOFT_GATE` IS INERT ON THE SHIPPING MERGE: IT CHANGES ZERO PIXELS ON THE DEFAULT "
     "BACKEND, AND IS THE THIRD KNOB FOUND TO DO NOTHING ON THE PATH IT SHIPS ON.** "
     "`bee-1-cpl` gaussian against unset differs on 0 of 98,898,048 px; `112MSDCF` on 0 of "
     "24,724,512 px. The comparator was commissioned in the same run, a planted 1-sample defect "
     "giving n_diff 1 and a null giving n_diff 0, so the zero is a real zero and not a dead "
     "instrument. Structural cause: `active_kernel()` has exactly one call site, `merge.rs:1455` "
     "inside `Estimator::new`, reachable only from `run_estimator`; `run_pyramid` never constructs "
     "an `Estimator`, a search of `pyramid.rs` for the estimator and soft-gate symbols returns "
     "zero occurrences, and `DEFAULT_MERGE_BACKEND` is Pyramid. On the estimator backend the same "
     "knob moves 59.1595% of pixels, so the kernel works and is simply unreachable by default. "
     "Any claim that the soft gate helped or hurt anything on the default path was measuring "
     "nothing. Follows `--exposure` as the same failure shape."),

    ("1870", "MEASURED", "V-KILLB0",
     "**A HARNESS CAN BE FULLY SENSITIVE TO REVERSAL AND COMPLETELY BLIND TO DELETION; "
     "SENSITIVITY TO ONE MUTATION CLASS PREDICTS NOTHING ABOUT ANOTHER.** "
     "`softverdict.py` reported 7 of 7 conclusion-flip arms caught, and deleting an entire "
     "commissioning arm left `caught == len(ARMS)` true, so it still printed BINDING CHECK PASSED. "
     "The seven original arms were all reversals; nothing in the design ever asked whether an arm "
     "could vanish. Repaired by pinning the arm count AND the arm names, after which the audit "
     "reads 8 of 8. This is the seventh independent lane tonight to find its own verifier blind "
     "to a class of defect it was never planted with, and the first where the blind class was "
     "deletion rather than reversal. Corollary adopted as method: a commissioning suite must plant "
     "reversal, deletion and a null, because without the null an always-red harness scores 100%."),

    ("1871", "CORRECTED", "ORCH",
     "**MY OWN BROADCAST COLLAPSED TWO DIFFERENT HALO INSTRUMENTS INTO ONE CLAIM, AND A BLANKET "
     "PURGE ON MY SAY-SO WOULD HAVE DELETED A LIVE FINDING.** I told fifteen lanes that no halo is "
     "demonstrated on any of the 26 masters and to purge halo language accordingly. True of "
     "`halo_profile.py` on the pyramid masters, which is what ships, and where 0 of 26 are "
     "demonstrated. NOT a statement about the estimator-versus-pyramid aura, which is a different "
     "instrument asking a different question and whose direction survived a dedicated attack: the "
     "estimator's aura measured deeper in all 17 conditioned readings across 4 subjects, excess "
     "294-3446 DN on flower-bud, 334-1127 DN on `bee-2-cpl`, 40-205 DN on tweezers, 5 DN on "
     "lead-1. Only the 28.5x multiplier is dead, withdrawn by its own author because the "
     "denominator crosses zero and the ratio spans 1.24x to 17.70x. Caught by a lane refusing a "
     "blanket instruction and checking what `ORCH-veiling.md:11858` actually said, which is that "
     "`halo_profile.py` was built for a different question. Ninth ORCH correction."),

    ("1872", "MEASURED", "V-KILLB0",
     "**TWO SOURCE DEFECTS I SUSPECTED IN THE MERGE ARE NOT DEFECTS, REPORTED BY THE LANE I HAD "
     "ASKED TO ATTACK THEM.** The winner is pinned at `merge.rs:1908` by `raw.max(1.0)` rather "
     "than trusted to a possibly-zero gap, so the division I feared cannot occur. `luma_sum` is "
     "weighted by `wl` at `merge.rs:1968` and `disagreement` divides by `wsum` at `merge.rs:2172` "
     "using a Kish effective count, numerator ws squared over wq and denominator ws minus wq over "
     "ws, which means the M111 section 15.6 divisor warning was already handled correctly. "
     "Recorded because a suspicion that dies on inspection is worth as much as one that lands, and "
     "because both were raised by me and refuted by the lane with every incentive to confirm them."),
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
    print("inserted %d rows after fact 1868 (line %d)" % (len(new_rows), at + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
