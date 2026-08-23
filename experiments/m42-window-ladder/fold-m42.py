"""Fold M42 — the window ladder for `tenengrad-sq`.

M42 ran inside the M17 agent as a re-task, so its rows arrived in the agent
response rather than in the report file: `M42-window-ladder-measured.md` has no
"Proposed SYNTHESIS entries" section. The rows are therefore inline here, which
is the opposite of the M16 fold and worth stating: for M16 the report was the
single source and the script parsed it; here the script IS the only written copy
until the report is annotated, which this fold also does.

Facts 480-491 (M42's reserved block, 480-499 — 492-499 stay free).
Disciplines 258-261, questions 103-105 (assigned here; M42 proposed them
unnumbered, as instructed, because §5 and §10 have collided twice).
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
DOC = "M42-window-ladder-measured.md"

FACTS = [
    (
        480,
        "M13's headline reproduces from an independent M42 harness: argmin **w13**, mean regret **3.1708**, worst **12.1110**, zero-step w40 ENDPOINT 0.0002, basin w11-w15.",
        "Facts 60/61/81 are **verified by a second implementation**, not merely re-run. Gate 1 has demonstrated power to reject — the tile-margin trap fired during M42.",
        "`experiments/m42-window-ladder/data/m42-analysis.txt`",
    ),
    (
        481,
        "The window optimum **MOVES with the operator**: `\\|grad\\|` argmin **w13**, `tenengrad-sq` argmin **w11** (mean regret 2.9789 vs 3.8393 at w13).",
        "A window optimum is a property of the operator/window **PAIR**, not of the window alone. Q1 was a real correctness risk, not a tidiness item.",
        "`data/edge-{109,119}MSDCF.csv` via `m42_analyse.py`",
    ),
    (
        482,
        "`tenengrad-sq` at w13 sits **+0.8604 DN** above its own minimum against a pre-registered **0.87 DN** basin — inside by **0.0096 DN**, 1.1% of the bar.",
        "`WINDOW_RADIUS = 13` **SURVIVES** the pre-registered test. It is the weakest possible pass and must never be quoted as \"13 is optimal\" for the squared operator.",
        "`data/m42-analysis.txt`",
    ),
    (
        483,
        "**0 of 6** independent subsets (2 stacks x 3 replicates) put `tenengrad-sq`'s argmin at 13; all six give w10 or w11. For `\\|grad\\|` it is **6/6 -> w13** with zero spread.",
        "The squared argmin is as well-determined as the magnitude's **and it is not 13**. Basin width alone hid this; independent argmins exposed it.",
        "`data/m42-uncertainty.txt`",
    ),
    (
        484,
        "Per stack, `tenengrad-sq` at w13 is +0.6075 DN on 109MSDCF (inside the basin) and **+1.1326 DN on 119MSDCF (outside it)**.",
        "The pooled pass is an **averaging artefact across stacks**. Consistent with fact 88: stack-level quantities do not transfer.",
        "`data/m42-uncertainty.txt`",
    ),
    (
        485,
        "`tenengrad-sq`'s **worst-case**-regret argmin is **w9** (13.1438 DN); w13's worst case is **19.8320 DN**, a **51% tail penalty**.",
        "The tail argues for a smaller radius more strongly than the mean does. Directly relevant once per-pixel confidence is calibrated on tail behaviour.",
        "`data/m42-analysis.txt`",
    ),
    (
        486,
        "The blind-spot cure is **radius-INVARIANT**: `tenengrad-sq` discrimination D = **0.1860 from w8 through w40**, unchanged. `\\|grad\\|` reaches exactly **1.0000 by w10** and stays there.",
        "Squaring breaks TV conservation **itself** (Cauchy-Schwarz: blur strictly reduces the integral of g-squared), not merely its asymptotics, so a wider box cannot restore blindness. **The radius choice stays a pure quality/noise tradeoff** and can be specified independently of fact 73.",
        "`data/blindspot-nonorm.csv`",
    ),
    (
        487,
        "On a **width-9 smooth ramp**, `tenengrad-sq` reads D = **0.6802** against `\\|grad\\|`'s 1.0000 — at every radius w8-w40. **This falsified M42's own registered prediction 3.**",
        "Fact 73's blind spot is **CLOSED on monotone steps and only HALF-CURED on smooth gradients** — specular falloff on a carapace, defocused backgrounds, petal edges. A new, open limitation of the M17 remedy that no radius fixes.",
        "`data/blindspot-nonorm.csv`",
    ),
    (
        488,
        "Fact 66 holds for the squared operator: cost is flat in radius, bound **<=1.020x** (`\\|grad\\|`) / **<=1.013x** (`tenengrad-sq`) over w1-w40. `tenengrad-sq` at **w11 and w13 both measure 3.226 ms/frame/Mpx** = **0.968x** the shipped operator.",
        "**Re-radiusing is free**, because `box_mean` is a running sum and O(1) in radius. M17's 0.96x cost win survives the radius change.",
        "`data/cost-measures.csv`, alternating passes, per-setting minimum",
    ),
    (
        489,
        "The naive cost ratio across M13's full ladder is 1.74x/1.79x, driven **entirely by `w0`**, which skips the box filter. Excluding it, the ladder is flat to **1.02%**.",
        "\"Cost varies 1.75x with radius\" would be a **false claim derived from a real table**. Degenerate arms must be excluded before quoting a spread.",
        "`data/m42-uncertainty.txt`",
    ),
    (
        490,
        "Merged noise N falls monotonically with radius above w1; `tenengrad-sq` N(w11) = 1.0890 vs N(w13) = 1.0849. Moving 13->11 costs **+0.0041 N (0.38%)**.",
        "Noise is the **only** axis preferring the larger radius, and by a margin ~200x smaller than the quality gain it costs.",
        "`data/noise-{109,119}MSDCF.csv`",
    ),
    (
        491,
        "Independent cross-milestone ties: `N(\\|grad\\|, w13)` = **1.08637** from M42's harness vs the shipped **1.0864**; `tenengrad-sq-w13` absolute `excess_dn` = **22.70** vs M17's independent **22.7013**.",
        "Two separate harnesses agree to five and six figures on quantities the corpus already published. Raises confidence in both milestones' machinery.",
        "`data/noise-*.csv`, `data/edge-*.csv`",
    ),
]

DISCIPLINES = [
    (
        258,
        "**Report independent argmins, not only basin width.** A pooled basin can comfortably contain a setting that *zero* independent subsets would select. M42's pooled basin said \"13 is fine\"; 6 of 6 independent subsets said w10-w11. Basin width answers \"is the surface flat here?\"; independent argmins answer \"would this data pick this value?\" — and only the second is a selection claim. Quote both, and never the first alone.",
    ),
    (
        259,
        "**A tuned pair must be re-validated whenever either half changes.** A window optimum belongs to the operator/window pair, not to the window. Shipping a new operator at a radius tuned for the old one is a defect *even when the radius happens to survive the test* — the survival is then luck, not evidence. Applies to every (estimator, hyper-parameter) pair this project ships, not just this one.",
    ),
    (
        260,
        "**Exclude degenerate arms before quoting a spread across a ladder.** M42's cost ladder reads 1.75x with `w0` included and 1.02x without it, because `w0` skips the box filter entirely and is not a member of the family being compared. A spread quoted over a ladder containing a non-member is a true number about a false set.",
    ),
    (
        261,
        "**When a script that produced a reported result has a bug in a section that produced NO output, still fix it in a new file.** Rule 15 protects reported numbers, and a silently-empty block reported none — but editing in place destroys the audit trail for what the script *did* report. M42 added `m42_uncertainty.py` rather than patching `m42_analyse.py`.",
    ),
]

QUESTIONS = [
    (
        103,
        "**Does any focus operator close the smooth-ramp blind spot?** `tenengrad-sq` takes discrimination D from 1.0000 to 0.6802 on a width-9 ramp\n    and **no radius in the w8-w40 ladder improves it** (fact 487). Ramps are the common macro case — specular falloff on a carapace, defocused\n    backgrounds, petal edges — and fact 73's original argument called them out by name. Half a cure on the most common case may be the largest\n    remaining defect in the focus operator.",
    ),
    (
        104,
        "**Is M13's planted-edge regret curve the same shape as a natural depth step's?** The entire `WINDOW_RADIUS` lineage — M13, M15, M17, M42 —\n    inherits **one plant**, and not one of those four milestones has tested whether its regret curve resembles a real occluding edge's.\n    M42 lists this first under what it could not measure. If the shapes differ, every radius number in the corpus moves together.",
    ),
    (
        105,
        "**Should worst-case regret be weighted, and how?** Mean regret selects w11; worst-case regret selects w9, and w13's tail penalty is **51%**\n    (19.83 DN vs 13.14 DN, fact 485). M42 explicitly declined to make this call unilaterally. It matters most once per-pixel confidence is\n    calibrated on tail behaviour, since a tail-weighted objective would also change what the confidence map is promising.",
    ),
]


def build_row(n, claim, consequence, source):
    prov = (
        f"M42 (MEASURED — {source}; pre-registered `21df0d8`; "
        f"see [`{DOC}`]({DOC})) — **NOT INDEPENDENTLY VERIFIED**"
    )
    row = f"| {n} | {claim} | {consequence} | {prov} |"
    if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
        raise SystemExit(f"row {n}: unescaped pipe")
    return row


def main():
    text = SRC.read_text(encoding="utf-8")

    present = {int(m) for m in re.findall(r"^\| (\d+) \|", text, re.M)}
    want = {n for n, *_ in FACTS}
    if present & want:
        raise SystemExit(f"fact collision: {sorted(present & want)}")

    dsec = re.search(r"^## 5\.", text, re.M)
    dend = re.search(r"^## ", text[dsec.end():], re.M)
    dseg = text[dsec.start():dsec.end() + dend.start()]
    dpresent = {int(x) for x in re.findall(r"^(\d+)\. \*\*", dseg, re.M)}
    if dpresent & {n for n, _ in DISCIPLINES}:
        raise SystemExit("discipline collision")

    qsec = re.search(r"^## 10\.", text, re.M)
    qpresent = {int(x) for x in re.findall(r"^(\d+)\. \*\*", text[qsec.start():], re.M)}
    if qpresent & {n for n, _ in QUESTIONS}:
        raise SystemExit("question collision")

    lines = text.split("\n")
    # anchor is 439, not 479: M40 (440-459) and M41 (460-479) have not folded yet,
    # so their blocks are still empty. 480-491 lands between 439 and 500 either way.
    idx = [i for i, l in enumerate(lines) if l.startswith("| 439 |")]
    if len(idx) != 1:
        raise SystemExit(f"expected one anchor row 439, got {len(idx)}")
    lines[idx[0] + 1 : idx[0] + 1] = [build_row(*f) for f in FACTS]
    text = "\n".join(lines)

    # disciplines: append after the highest-numbered item (257)
    dsec = re.search(r"^## 5\.", text, re.M)
    dend = re.search(r"^## ", text[dsec.end():], re.M)
    lo, hi = dsec.start(), dsec.end() + dend.start()
    seg = text[lo:hi]
    m = re.search(r"^257\. \*\*", seg, re.M)
    if not m:
        raise SystemExit("discipline 257 not found")
    nxt = re.search(r"^\d+\. \*\*", seg[m.end():], re.M)
    ins = lo + (m.end() + nxt.start() if nxt else len(seg.rstrip("\n")) + 1)
    text = text[:ins] + "".join(f"{n}. {d}\n\n" for n, d in DISCIPLINES) + text[ins:]

    # questions: append at end of §10 (the final section)
    text = text.rstrip("\n") + "\n\n" + "".join(f"{n}. {q}\n\n" for n, q in QUESTIONS)

    SRC.write_text(text, encoding="utf-8")
    print(
        f"facts {[n for n, *_ in FACTS]}, "
        f"disciplines {[n for n, _ in DISCIPLINES]}, "
        f"questions {[n for n, _ in QUESTIONS]}"
    )


if __name__ == "__main__":
    main()
