"""Fold M40 - the verification that refutes the orchestrator's own repair.

M40 was asked to audit `SELECTION_INFLATION = 1.074`, a constant I introduced.
Its verdict is that the repair does not stand. The arithmetic reproduced to four
decimals; as rule 24 predicts, every defect was a CHOICE. I am folding it in
full, including the rows that are most damaging to my own work.

Two format notes:

1. M40 delivered TWO-column rows (`| # | Fact |`) with provenance embedded in
   the fact text. SYNTHESIS is four columns. The fact text is taken verbatim
   from M40's file -- parsed, not retyped -- and I supply the Consequence
   column myself, drawn only from M40's own §11 recommendations and its section
   findings. Where I add an inference beyond what M40 wrote, it is marked.

2. M40 proposed disciplines and questions WITHOUT numbers, as instructed.
   Numbers are assigned here: disciplines 263-267, questions 106-110.

This fold also RE-RULES four facts M40 was asked to check (428-431) and
RE-OPENS fact 341, which was mine.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
RPT = pathlib.Path("docs/research/M40-VERIFICATION.md")
DOC = "M40-VERIFICATION.md"

CONSEQUENCE = {
    440: "**The constant has no defined meaning, independently of its value.** Extends rule 10 from a reporting rule to a units rule: spatial and temporal quantities may not be multiplied even when the arithmetic reproduces.",
    441: "A figure the corpus published as a single number takes a **1.60x range** over the free choice of reference frame. No `x/middle-frame` ratio in this project is a measurement until that sweep is reported beside it.",
    442: "The flat-ROI ratio is a ratio of two **structure-dominated** quantities, so it was never measuring the winner's curse it was introduced to measure.",
    443: "**It is not a constant.** One of those six readings is 1.0739x, which is the shipped value — so the published number was one draw from a distribution presented as a property.",
    444: "**The selection content of the worst reading is 0.0001.** A fixed-frame arm with no selection at all reproduces it, which means the estimator is not measuring selection.",
    445: "The honest per-pixel selection inflation is **1.012x-1.038x**, roughly half the shipped 1.074x, and it differs between the pixel and gradient domains.",
    446: "**1.074 exceeds its own ceiling.** On a plant built to maximise the winner's curse the operator cannot produce more than 1.045x. A constant above the maximum its own mechanism can generate is refuted without needing a better estimate.",
    447: "**C1 and the detail metric need different constants** (ratio 0.681-0.693, stable across four gates). One scalar cannot serve both consumers.",
    448: "`selection_inflation(n>=2) = 1.0` is **wrong at every n tested**. The decay is smooth from 1.0770 to 1.0220, so the two-branch step puts a 7.4-point discontinuity through the 41.66% of the plane that sits at n=1.",
    449: "The repair reaches **only the n=1 stratum**, over-predicts there at gate 0, and leaves gates 1.0 and 2.0 essentially unrepaired. It is not a repair at working gates.",
    450: "**Inflating C1 changes no flagged pixel.** A quantile channel is invariant to any order-preserving transform of its input, so \"the confidence vector is unchanged\" is never evidence about a calibration constant — including in my own defence of this repair.",
    451: "The whole 5% C1 tail is n=1 pixels in both arms, so the new definition **cannot flip fact 281's sign**; it saturates the composition instead.",
    452: "**A fourth consumer existed and nobody enumerated it.** `merge_cmd.rs:912` prints the repaired quantity from a different formula and still shows 1.0000x at gate 0 — the exact number fact 341 filed as the defect. The repair did not reach the place the defect was reported from.",
    453: "That column **reports a better noise gain than the merge achieves**, by 2.4-5.9% (Jensen; equality only for constant n). It is a user-facing overstatement independent of the inflation question.",
    454: "**The correction crosses zero and lands further from truth than the defect it replaced**, and the shipped `max(0,.)` hides it. This is M40's decisive argument that shipping 1.074 is worse than shipping nothing.",
    455: "**Fact 341's premise is false.** The ROI I called \"a flat ROI, where no detail can exist\" spans 3.5x in per-frame detail, and the modal winner carries 1.267x the reference frame's detail unmerged. The +35.47% I attributed to a merge defect is mostly the reference frame's own defocus.",
    456: "The inflation that would zero the flat-ROI credit **tracks frame sharpness, not noise** — which is the direct evidence that the quantity being corrected is optical, not statistical.",
    457: "**The spurious credit is removed on one ROI of one stack and survives at +31.5% on another.** A repair that works on the ROI it was fitted to and fails elsewhere is a fit, not a fix. Consistent with fact 88: stack-level quantities do not transfer.",
    458: "**The two-branch invariant is the right SHAPE** — n=1 is the modal configuration at a working gate, not a gate-0 artefact — even though its constant is wrong. Keep the structure, re-derive the number.",
    459: "**No input could have failed the retired test.** Confirms and strengthens fact 429, and is the cleanest example in the corpus of rule 20's necessity: a test nobody could fail was guarding the project's central invariant.",
}

DISCIPLINES = [
    (263, "**A ratio against a single reference frame is not a measurement until the reference has been swept.** Any published `x/middle-frame` figure must carry the range it takes over all N choices of reference. On this project that range has been as wide as **1.0000x-1.5989x** for a figure published as a single number."),
    (264, "**Never move a number between the spatial and temporal domains.** Extends rule 10. `flat_roi_stats` is spatial; `predicted_sigma` is temporal; a constant read off one and multiplied into the other **has no defined meaning even when the arithmetic reproduces to four decimals** — which it did."),
    (265, "**A \"flat\" control ROI must be certified detail-free by the metric under test, not by spatial contrast.** Report the per-frame span of that metric across the focus sweep beside the ROI. A 3.5x span disqualifies the ROI as a null, and one was used as a null for exactly that long."),
    (266, "**When a constant is introduced, enumerate its consumers by grepping for the reported QUANTITY, not for the function name.** M40 found a fourth consumer that prints the repaired quantity from a different formula and therefore still displayed the unrepaired value after the repair shipped."),
    (267, "**A quantile channel cannot validate the scale of its own input.** C1's mask is invariant to any order-preserving change to `predicted_sigma`, so \"the confidence vector is unchanged\" is never evidence about a calibration constant. It was used as exactly that evidence."),
]

QUESTIONS = [
    (106, "**Does the C1 mask move at a wider confidence tail (25-50%)**, where the boundary crosses into n >= 2 pixels? M40 measured only the shipped 5% tail, where fact 450 shows the mask is\n    completely invariant. If the mask is invariant at every tail width, the C1 channel cannot be validated by any experiment of this shape and needs a different instrument."),
    (107, "**What is the selection inflation on REAL data as a function of n?** The naive stratification confounds n with scene flatness — pixels with large n are pixels where many frames agreed, which is\n    also where the scene is flat. A matched-content stratification is needed before any real-data curve can be read as a selection effect."),
    (108, "**Does fixed-pattern noise lift the true inflation above the pure-noise plant's ceiling of 1.045?** PRNU, dark current and M16's orientation FPN are all absent from M40's plant. If any of them\n    raises the winner's curse, then fact 446's ceiling — currently the strongest single argument against 1.074 — is not a bound. This is cheap to test once the flat-field campaign lands."),
    (109, "**Should `SELECTION_INFLATION` be two constants, a per-n curve, or nothing at all?** Fact 447 gives a stable pixel/gradient split (~1.045 and ~1.031); fact 448 gives a smooth curve in n.\n    A fourth option M40 raises is that the detail metric should stop using a model noise term entirely and use a **paired difference of two independent merges** instead, which needs no constant."),
    (110, "**Should `report_flat_roi`'s banner still quote fact 19's 1.253x?** Neither M39 nor M40 can reproduce it and the operator that produced it is retired, yet it is printed live to users."),
]


def parse_facts():
    text = RPT.read_text(encoding="utf-8")
    m = re.search(r"^### New facts", text, re.M)
    if not m:
        raise SystemExit("'### New facts' not found in M40's report")
    seg = text[m.end():]
    stop = re.search(r"^### ", seg, re.M)
    seg = seg[: stop.start()] if stop else seg

    out = {}
    for line in seg.split("\n"):
        if not line.startswith("| "):
            continue
        c = [x.strip() for x in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(c) == 2 and c[0].isdigit():
            out[int(c[0])] = c[1]
    if sorted(out) != list(range(440, 460)):
        raise SystemExit(f"expected facts 440-459, got {sorted(out)}")
    return out


def build_row(n, claim):
    cons = CONSEQUENCE[n]
    prov = f"M40 (VERIFICATION of the orchestrator's own repair; see [`{DOC}`]({DOC})) — **INDEPENDENT**"
    row = f"| {n} | {claim} | {cons} | {prov} |"
    if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
        raise SystemExit(f"row {n}: unescaped pipe")
    return row


def main():
    facts = parse_facts()
    text = SRC.read_text(encoding="utf-8")

    present = {int(m) for m in re.findall(r"^\| (\d+) \|", text, re.M)}
    if present & set(facts):
        raise SystemExit(f"fact collision: {sorted(present & set(facts))}")

    dsec = re.search(r"^## 5\.", text, re.M)
    dend = re.search(r"^## ", text[dsec.end():], re.M)
    dpresent = {int(x) for x in re.findall(r"^(\d+)\. \*\*", text[dsec.start():dsec.end() + dend.start()], re.M)}
    if dpresent & {n for n, _ in DISCIPLINES}:
        raise SystemExit("discipline collision")
    qpresent = {int(x) for x in re.findall(r"^(\d+)\. \*\*", text[re.search(r"^## 10\.", text, re.M).start():], re.M)}
    if qpresent & {n for n, _ in QUESTIONS}:
        raise SystemExit("question collision")

    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("| 439 |")]
    if len(idx) != 1:
        raise SystemExit("anchor 439 not unique")
    lines[idx[0] + 1 : idx[0] + 1] = [build_row(n, facts[n]) for n in sorted(facts)]
    text = "\n".join(lines)

    dsec = re.search(r"^## 5\.", text, re.M)
    dend = re.search(r"^## ", text[dsec.end():], re.M)
    lo, hi = dsec.start(), dsec.end() + dend.start()
    seg = text[lo:hi]
    m = re.search(r"^262\. \*\*", seg, re.M)
    if not m:
        raise SystemExit("discipline 262 not found")
    nxt = re.search(r"^\d+\. \*\*", seg[m.end():], re.M)
    ins = lo + (m.end() + nxt.start() if nxt else len(seg.rstrip("\n")) + 1)
    text = text[:ins] + "".join(f"{n}. {d}\n\n" for n, d in DISCIPLINES) + text[ins:]

    text = text.rstrip("\n") + "\n\n" + "".join(f"{n}. {q}\n\n" for n, q in QUESTIONS)

    SRC.write_text(text, encoding="utf-8")
    print(f"facts {sorted(facts)}")
    print(f"disciplines {[n for n, _ in DISCIPLINES]}, questions {[n for n, _ in QUESTIONS]}")


if __name__ == "__main__":
    main()
