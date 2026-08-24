"""Fold 27 -- the orchestrator retracts fact 1235, discipline 605, and the
1.1288 in fact 1237, and records why M97's ground truth could not have
detected the defect it was pointed at.
"""
import io
import re

P = "docs/research/SYNTHESIS.md"
L = io.open(P, encoding="utf-8").read().split("\n")


def check(row):
    n = len(re.findall(r"(?<!\\)\|", row))
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, row[:160])
    return row


F1235 = check(
    "| 1235 | ~~**THE REGISTERED RENDER IS VISIBLY SHARPER THAN ITS OWN "
    "FIELD-OF-VIEW-MATCHED NULL.**~~ **RETRACTED BY ITS OWN AUTHOR, fact 1250.** "
    "The two renders differ by **1.25% in magnification**, so the crops the "
    "orchestrator called co-located were not comparing like with like, and at "
    "100% on fine bristles 1.25% reads as crisper. With scale matched by "
    "nearest-neighbour resampling the crops are indistinguishable. The claim is "
    "withdrawn; M97's independent ruler measurement stands unopposed. | The "
    "orchestrator made the error of discipline 606 a second time in one night, "
    "at 100% instead of thumbnail scale, having written that discipline four "
    "hours earlier. Retained struck through rather than deleted so the record "
    "shows what was believed and for how long. | orchestrator (MEASURED, then "
    "REFUTED by the same author) |")

F1237 = check(
    "| 1237 | ~~**PER-REGION TENENGRAD RATIOS CHANGE SIGN ACROSS THE SAME "
    "FRAME.**~~ **RETRACTED, fact 1250.** The sign change was the 1.25% "
    "magnification artefact. Scale-matched, every region moves below 1 and none "
    "reverses: wing-venation 0.9285, thorax-hair 0.9834, head-eye 0.9633, "
    "whole-frame 0.9747. | The `1.1288` for leg-spines was flagged unverified "
    "when it was folded and handed to M97 with that caveat. It was not merely "
    "unverified, it was wrong, which is worse: a caveat does not stop a number "
    "being used. Discipline 610. | orchestrator (MEASURED, then REFUTED) |")

NEW = [
    check(
        "| 1250 | **THE ALIGNED AND REGISTRATION-DISCARDED RENDERS DIFFER BY "
        "1.25% IN MAGNIFICATION, WHICH IS WHY ONE LOOKED SHARPER.** Cross-"
        "correlating `bee-3-ALIGNED.tif` against `bee3-zoomnull.tif` over a "
        "scale ladder 0.970-1.030 on a central 1400^2 window, nearest-neighbour "
        "only so neither arm can be blurred by the probe: NCC peaks at scale "
        "**0.9875 (NCC 0.9038)**, against 0.8578 unscaled. The peak is "
        "unambiguous and 5 ladder steps clear of the endpoints. | The "
        "orchestrator wrote this probe to falsify its own fact 1235 after M97 "
        "measured a contradicting result, rather than to defend it. Both the "
        "visual claim (fact 1235) and the per-region sign change (fact 1237) "
        "die on it, and discipline 605's premise dies with them: with the claim "
        "withdrawn the metric and the eye agree that alignment does not "
        "visibly sharpen this render. | orchestrator (MEASURED); "
        "`experiments/ORCH-drift-check/selfcheck.py`, `matched.py` |"),
    check(
        "| 1251 | **EDGE STRAIGHTNESS IS ANALYTICALLY BLIND TO FOCUS BREATHING, "
        "SO M97'S NULL RESULT DOES NOT YET EXONERATE ALIGNMENT.** Breathing is "
        "a similarity transform -- a magnification change about the optical "
        "axis -- and similarities map straight lines to straight lines. A "
        "straight edge photographed through an uncorrected breathing bracket "
        "comes out straight. M97's +4.252 px sensitivity to *planted* "
        "misregistration does not rescue the metric, because the plant is a "
        "translation and straightness responds to translations while being "
        "blind to scale. | M97 measured +0.038 px of straightening from "
        "alignment and concluded alignment does not help. The measurement is "
        "sound; the inference is not licensed, because the instrument cannot "
        "express the defect. Not a criticism of M97 -- the orchestrator named "
        "the target without explaining what it had to show. | orchestrator "
        "(ARGUED, geometric); M97's measurement MEASURED |"),
    check(
        "| 1252 | **A FLAT-ON TARGET CANNOT TEST A FOCUS STACKER, BECAUSE A "
        "STACK THAT DOES NOT SPAN DEPTH IS NEARLY A SINGLE FRAME.** "
        "`flat-on-ruler-cpl` sits at essentially constant depth, so every pixel "
        "elects from nearly the same frame and there is almost no inter-frame "
        "magnification difference for alignment to correct. The corpus's "
        "`highly-angled-ruler-mm-cpl` (299 frames) varies depth across the "
        "field, so regions elect from widely separated frames carrying "
        "different magnifications, making the residual scale error "
        "**differential across the frame** -- which does bend straight lines "
        "and does distort tick spacing. | Doubly suppressed on the flat target: "
        "once by fact 1251's geometry, once by the absent depth span. The "
        "angled ruler also unlocks the strongest ground truth the project has "
        "and has never used -- **millimetre tick spacing across the field is "
        "known a priori**, so scale error is measurable in absolute units "
        "rather than by comparison. | orchestrator (ARGUED); capture inventory "
        "MEASURED |"),
]

DISC = [
    "610. **A CAVEAT DOES NOT STOP A WRONG NUMBER FROM BEING USED, SO PREFER "
    "NOT TO SHIP IT.** The orchestrator folded `leg-spines 1.1288` explicitly "
    "flagged unverified and handed it to M97 with the caveat attached; it was "
    "the headline evidence that the sharpness metric reverses by region, and "
    "it was an artefact of a 1.25% magnification difference. An unverified "
    "number that supports the author's thesis will be read as support and the "
    "flag will be read as modesty. Either verify it before folding or state "
    "the mechanism that would make it wrong, so the reader can check it "
    "instead of discounting it. (facts 1237, 1250)",

    "611. **BEFORE ACCEPTING A NULL RESULT, ASK WHETHER THE INSTRUMENT CAN "
    "EXPRESS THE DEFECT -- SENSITIVITY TO A PLANT IS NOT ENOUGH.** M97's "
    "straightness metric detected +4.252 px of planted misregistration and "
    "+0.038 px from alignment, and the natural reading is that alignment does "
    "nothing. But the plant and the defect are different transforms: "
    "straightness responds to translation and is analytically blind to the "
    "scale change breathing actually causes. **A plant validates a metric only "
    "if the plant has the same form as the defect.** This is discipline 24's "
    "'plants must be able to express the failure' turned on the metric rather "
    "than the data. (facts 1251, 1252)",

    "612. **WHEN THE ORCHESTRATOR AND A SUBORDINATE DISAGREE, THE ORCHESTRATOR "
    "TESTS ITSELF FIRST.** M97 reported a measurement contradicting a fact the "
    "orchestrator had folded from its own eyes. The orchestrator wrote a probe "
    "designed to kill its own claim, and the claim died. Rank is not evidence, "
    "and an orchestrator that defends its folded facts against subordinate "
    "measurement corrupts the corpus at the one point where nothing downstream "
    "can catch it -- every other fact in this table has been through an "
    "adversarial reader, and the orchestrator's have not. (facts 1235, 1250)",
]

# Disciplines sit at a higher line index than the fact table, so patch the
# discipline list first and the fact indices stay valid.
i605 = next(i for i, l in enumerate(L) if l.startswith("605. "))
assert "ANTI-CORRELATED WITH IMAGE QUALITY" in L[i605]
L[i605] = (
    "605. ~~**A GLOBAL SHARPNESS METRIC CAN BE ANTI-CORRELATED WITH IMAGE "
    "QUALITY, BECAUSE MISREGISTRATION MANUFACTURES GRADIENT ENERGY.**~~ "
    "**RETRACTED, fact 1250.** The premise was the orchestrator's visual claim "
    "that the registered render is sharper; that claim was a 1.25% "
    "magnification artefact and has been withdrawn. With it withdrawn the "
    "metric and the eye agree, and there is no measured instance of "
    "anti-correlation. The *mechanism* remains plausible -- a doubled edge does "
    "carry two gradients -- but it is now ARGUED with no supporting "
    "observation, and no milestone may build on it. (facts 1235, 1237, 1250)")

i609 = next(i for i, l in enumerate(L) if l.startswith("609. "))
end = i609 + 1
while end < len(L) and L[end].strip() and not re.match(r"^\d+\. ", L[end]):
    end += 1
L[end:end] = [""] + [d for pair in ((d, "") for d in DISC) for d in pair][:-1]

ilast = max(i for i, l in enumerate(L) if l.startswith("| 12"))
assert L[ilast].startswith("| 1249 |"), L[ilast][:80]
L[ilast + 1:ilast + 1] = NEW

for i, l in enumerate(L):
    if l.startswith("| 1235 |"):
        L[i] = F1235
    elif l.startswith("| 1237 |"):
        L[i] = F1237

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("wrote facts 1250-1252, disciplines 610-612")
print("retracted: fact 1235, fact 1237, discipline 605")
