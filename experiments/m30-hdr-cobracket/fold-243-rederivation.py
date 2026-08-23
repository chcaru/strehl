"""Re-derive fact 243's HDR verdict, which rested partly on the withdrawn fact 242.

M31-V withdrew fact 242 as a rule-4 violation and left an explicit instruction on
the row: "Fact 243's HDR verdict rests partly on it and must be re-derived."
This is that re-derivation, done by the orchestrator.

Three things it establishes, all checked against primary sources rather than
against the milestone's prose:

  1. M31-V's "31x31, the shipped scale" is CORRECT, and non-obviously so. The
     shipped constants are WINDOW_RADIUS = 13 (a 27x27 focus box) and
     REGULARISER_RADIUS = 8 (a 17x17 regulariser). Neither is 31. But
     merge::regularise box-means the focus field, which focus::compute has
     already box-meaned, so the two kernels COMPOSE, and boxes compose
     additively in variance: 60.667 + 24.000 = 84.667, whose variance-equivalent
     single box is 31.89 taps. R=15 is right. Recorded so that a future reader
     who compares 31 against the constants does not "correct" a correct number.

  2. Fact 243 quotes 1.89% for the +2 EV clipping penalty. M30's OWN output file
     contains 7.05% for the same quantity at the frame the merge actually
     gathers. The milestone quoted the weaker of two numbers its own script
     wrote, and the weaker one understates its own conclusion by 3.7x.

  3. The verdict itself SURVIVES, but the reason changes sign. M30 argued the
     highlight case for exposure bracketing was "roughly half what a whole-stack
     figure suggests" because selection dodges clipping. Withdrawing fact 242
     removes most of that dodge, so the case for an exposure pass is STRONGER
     than M30 concluded, not weaker.

Writes facts 432-435 and discipline 255, and marks fact 243 in place.
Fact block claimed programmatically per rule 25; 432-439 verified free.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")

# --- the mark appended to fact 243's provenance cell -------------------------
MARK_243 = (
    " — **RE-DERIVED by the orchestrator after fact 242's withdrawal; the verdict "
    "STANDS and its own evidence was understated 3.7x.** See facts 432-435. The "
    "recommendation (support, do not default, trigger per stack) survives intact, "
    "but **the argument for it inverts**: M30 reached it partly by reasoning that "
    "selection already dodges half the clipping, and that dodge is now measured at "
    "1.32x rather than 2.3x, so **the highlight case is stronger than M30 thought, "
    "not weaker**. The `−2 EV, not +2 EV` direction is unaffected and is "
    "reinforced. **The 1.89% in this row should read 7.05%**"
)

# --- new rows ----------------------------------------------------------------
ROWS = [
    (
        432,
        "**M31-V's \"31x31, the shipped scale\" is correct, and the shipped constants do not say 31.** "
        "`WINDOW_RADIUS = 13` gives a 27x27 focus box; `REGULARISER_RADIUS = 8` gives a 17x17 "
        "regulariser. `merge::regularise` box-means the focus field that `focus::compute` has "
        "**already** box-meaned, so the kernels compose, and boxes compose additively in variance: "
        "`60.667 + 24.000 = 84.667`, whose variance-equivalent single box is **31.89 taps**",
        "**Recorded to protect a correct number from a plausible-looking correction.** A reader "
        "checking M31-V against the code finds 27 and 17, sees 31 in neither, and has every reason "
        "to think the verification swept the wrong scale — the orchestrator did think exactly that, "
        "and spent a pass proving itself wrong. The general form: **when two smoothing stages are "
        "applied in series, the scale that matters downstream is neither of their widths**, and a "
        "milestone that names the composed scale is more right than one that names a shipped "
        "constant. Cite this row alongside any future reading of the 1.4x",
        "orchestrator (DERIVED, arithmetic verified; kernel composition verified against "
        "`merge.rs:137` and `focus.rs:212`) — **NOT INDEPENDENTLY VERIFIED**",
    ),
    (
        433,
        "**Fact 243 quotes the weaker of two numbers M30's own script wrote.** The row states "
        "**1.89%** newly clipped at +2 EV on `coffee-bean`. That is `clip_at_p2` from script 02, "
        "measured at the **middle** frame. `01-dynamic-range.json` — the same milestone, the same "
        "stack, the same run — records `new_clip_at_p2 = 0.07049`, i.e. **7.05%**, measured at the "
        "**best-focus** frame, which is the frame the merge actually gathers. **3.7x**",
        "**The milestone understated its own conclusion.** Fact 243's point is that +2 EV is the "
        "wrong direction for highlights, and the number that makes that point hardest was sitting "
        "in its own output file, unquoted. This is not an arithmetic error and no recomputation "
        "would have found it — **it is a choice of which frame to report**, which is exactly the "
        "defect class rule 24 names. New discipline 255: **before quoting a milestone's number, "
        "grep its own artifacts for the same quantity**; where two exist, the row must say which "
        "condition each belongs to and why the quoted one was chosen",
        "orchestrator (MEASURED — read directly from "
        "`experiments/m30-hdr-cobracket/out/01-dynamic-range.json` and `02-fixed-light.json`, "
        "not from M30's prose; independently corroborates M31-V correction 3) — "
        "**NOT INDEPENDENTLY VERIFIED**",
    ),
    (
        434,
        "**Re-derived verdict on HDR co-bracketing: unchanged in what it recommends, inverted in "
        "why.** The three supports of fact 243 fare differently under M31-V. *Allocation "
        "neutrality* (fact 240) is **CONFIRMED** — re-derived by hand and by Monte Carlo — so "
        "\"do not default it\" stands. *The clipping dodge* (fact 242) is **WITHDRAWN**: gathered "
        "frames clip at **0.1293%** against a random-frame null of **0.1710%**, a **1.32x** "
        "advantage, not 2.3x. *The direction* (−2 EV, not +2 EV) is **STRENGTHENED** by fact 433",
        "**Support it, do not default it, trigger it per stack — but the trigger fires roughly "
        "twice as often as M30 implied.** M30's reasoning was that highlights are "
        "disproportionately out of focus, so a selector already avoids much of the clipping and "
        "the highlight case is \"roughly half what a whole-stack figure suggests\". At the scale "
        "the pipeline actually ships, that halving is 1.32x and mostly gone. **The conclusion "
        "survives on a weaker premise, which means it is now better supported than when it was "
        "written**: less of it rests on the selector being clever. R19's advisory must compute its "
        "trigger at the **regularised** gathered frames",
        "orchestrator (DERIVED from facts 240/242-as-corrected/433; inputs MEASURED by M30 and "
        "M31-V) — **NOT INDEPENDENTLY VERIFIED**",
    ),
    (
        435,
        "**And 7.05% is a lower bound, by the same mechanism that killed fact 242.** "
        "`new_clip_at_p2` is evaluated at a **raw-argmax** best frame. Fact 242's measured "
        "mechanism is that the argmax *flees* clipped frames, because clipping flattens the local "
        "gradient (median focus 262.26 clipped vs 311.11 unclipped). So the frames it evaluates "
        "are systematically **dimmer at clip-prone pixels** than the regularised winner the merge "
        "actually gathers, and a dimmer pixel newly clips less at +2 EV",
        "**The same rule-4 violation biases two numbers in opposite directions, and only one of "
        "them was caught.** It made fact 242's clipping advantage look 1.7x too good and it makes "
        "fact 433's +2 EV penalty look too small. **A defect in a shared upstream estimator does "
        "not have a single sign downstream** — it must be re-propagated through every consumer "
        "rather than corrected once at the source. Worth a measurement: re-run "
        "`new_clip_at_p2` at R=15 and read the true penalty",
        "orchestrator (ARGUED from fact 242's measured mechanism; **the sign is derived, the "
        "magnitude is not measured**) — **NOT INDEPENDENTLY VERIFIED**",
    ),
]

DISCIPLINE_255 = (
    "255. **Grep a milestone's own artifacts before quoting its number.** Fact 243\n"
    "     quoted 1.89% for a penalty its own `01-dynamic-range.json` recorded at\n"
    "     7.05%, understating the milestone's own conclusion by 3.7x. The two figures\n"
    "     were the same quantity at different frames, and the prose named neither\n"
    "     condition. No recomputation finds this, because both numbers are correct —\n"
    "     it is a **choice of reporting condition**, the defect class of rule 24.\n"
    "     Where a milestone's outputs hold two values for one quantity, the fact row\n"
    "     must state which condition each belongs to and why the quoted one was\n"
    "     chosen. See facts 433 and 435.\n"
)


def build_row(n, claim, consequence, provenance):
    row = f"| {n} | {claim} | {consequence} | {provenance} |"
    body = row[1:-1]
    if body.count("|") != 3:
        raise SystemExit(
            f"row {n}: {body.count('|')} interior pipes, need exactly 3 — "
            "an unescaped pipe in the text will break the table"
        )
    return row


def main():
    text = SRC.read_text(encoding="utf-8")
    lines = text.split("\n")

    # 1. mark fact 243 in place, appending inside its final cell
    hits = [i for i, l in enumerate(lines) if re.match(r"^\| 243 \|", l)]
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one fact-243 row, found {len(hits)}")
    i = hits[0]
    if not lines[i].rstrip().endswith("|"):
        raise SystemExit("fact 243 row does not end in a pipe")
    before = lines[i].count("|")
    lines[i] = lines[i].rstrip()[:-1].rstrip() + MARK_243 + " |"
    if lines[i].count("|") != before:
        raise SystemExit("marking fact 243 changed its pipe count")

    # 2. insert the new rows after fact 431
    hits = [j for j, l in enumerate(lines) if re.match(r"^\| 431 \|", l)]
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one fact-431 row, found {len(hits)}")
    at = hits[0] + 1
    new = [build_row(*r) for r in ROWS]
    lines[at:at] = new

    # 3. append discipline 255 after 254
    joined = "\n".join(lines)
    m = re.search(r"^254\. \*\*.*?(?=\n\d+\. \*\*|\n## |\Z)", joined, re.S | re.M)
    if not m:
        raise SystemExit("could not locate discipline 254")
    end = m.end()
    if not joined[:end].endswith("\n"):
        joined = joined[:end] + "\n" + DISCIPLINE_255 + joined[end:]
    else:
        joined = joined[:end] + DISCIPLINE_255 + joined[end:]

    SRC.write_text(joined, encoding="utf-8")
    print(f"marked fact 243; inserted facts {ROWS[0][0]}-{ROWS[-1][0]}; added discipline 255")


if __name__ == "__main__":
    main()
