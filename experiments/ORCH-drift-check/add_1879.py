"""Bank facts 1879-1881 from V-GATHER's wind-down."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ANCHOR_PREFIX = "| 1878 | MEASURED | V-SPEED |"

ROWS = [
    ("1879", "MEASURED", "V-GATHER",
     "**`printcert4.py`'s `load()` RETURNS AN EMPTY DICT FOR A MISSING INPUT, WHICH IN AN OFF/ON "
     "A/B MAKES THE BROKEN ARM SCORE BETTER THAN THE WORKING ONE.** Harmless today because all "
     "five JSONs are tracked in Git and always present. Under the OFF/ON comparison BUILD-DEFECT "
     "was about to run, a producer that fails on one arm yields no axis reporting FAIL, because "
     "there is nothing to fail on; the subject count silently falls; and the pooled verdict, "
     "computed over the survivors, IMPROVES. A skip scoring as a pass, in the one place where it "
     "inverts the result. Found by a lane reading the code to decide what was safe to delete, and "
     "deliberately NOT fixed by the finder on the grounds that silently changing an instrument "
     "another lane depends on, during wind-down, without re-commissioning, is worse than naming "
     "it. Routed to the owner with a required guard: both arms must report the same subject count "
     "or the run fails, and the guard must be commissioned by deleting an input and requiring a "
     "non-zero exit. Related hazard in the same script family: `SEAL_DIR` is hardcoded at "
     "`rimaxis.py:52`, so a two-tree A/B silently reads the same tree twice and the arms agree "
     "perfectly for the stupidest possible reason."),

    ("1880", "CORRECTED", "V-GATHER",
     "**AN INERT KNOB AND AN EFFECTIVE KNOB AIMED AT THE WRONG QUANTITY PRODUCE THE IDENTICAL "
     "DISAPPOINTMENT AND REQUIRE OPPOSITE RESPONSES.** ORCH listed the per-band gate floor "
     "alongside `STREHL_SOFT_GATE` and `--exposure` as knobs doing nothing on their shipping "
     "path. Refused by the lane that measured it: the gate floor demonstrably CHANGED the image, "
     "which is precisely why Part 16 concludes it acts as a denoiser. What it did not do is move "
     "the RIM. That is a statement about which quantity it reaches, not about whether it reaches "
     "anything. One gets deleted, the other gets re-aimed, and collapsing them would have thrown "
     "away a working component. The dead-knob count is therefore two, not three, plus one "
     "component that works on a quantity nobody wanted moved."),

    ("1881", "MEASURED", "V-GATHER",
     "**THIRTEEN RIM FAILURES AT TIGHT SCALE ON THE SHIPPING MASTERS, AT A SCALE THE HALO "
     "REFUTATION NEVER REACHED, AND NO SECOND LANE HAS SCORED THEM.** `rimv6` walks a contiguous "
     "±12 px with its reference INSIDE the same profile; `halo_profile.py` walks 2-120 px against "
     "a 400-900 px reference. The scales are disjoint, so the 0-of-26 refutation does not reach "
     "the rim axis and the 13 FAILs do not rescue `halo_profile`. Provenance confirmed from "
     "source rather than assumed: `rimaxis.py:52` sets `SEAL_DIR` to `acceptance\\SHIP-V4` and "
     "L185-194 enumerate the SHIP-V4 TIFFs, which are default-backend PYRAMID masters. So these "
     "are not the estimator aura and must not be read as corroborating it. Consequence for the "
     "product: the shipping masters are rim-UNEXAMINED at tight scale, which is not the same as "
     "rim-clean, and no print-readiness claim may rest on the halo refutation alone. "
     "`coffee-bubbles` now has two independent reasons not to lean on it, REFUSED on the rim axis "
     "and never band-qualified."),
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
    print("inserted %d rows after fact 1878 (line %d)" % (len(new_rows), at + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
