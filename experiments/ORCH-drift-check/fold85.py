"""Fold M104c's MTF result, the magnification-bias defect, and my duplication error."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1440,
     "**A SECOND SLANTED-EDGE MTF INSTRUMENT PASSES FOUR PRE-REGISTERED BARS, AND `flat-on-ruler-cpl` "
     "STILL CANNOT EXERCISE IT -- BECAUSE THE RULER WAS SHOT SQUARE.** Bars registered before "
     "measurement: analytic sigma=2.0/3.0 recovered to **+0.03%/+0.36%**; positive control "
     "MTF50(3)/MTF50(2) = **0.6689 against 0.6667 predicted (+0.33%)**; null of two disjoint crops of one "
     "image **+0.00%**. On the real stack, **83 of 103** high-contrast vertical ROIs fit within **+/-1 "
     "deg** of vertical, median **+0.01 deg**, and only **4 of 103** reach the usable 2-12 deg band, all "
     "at marginal contrast. **Contrast is not the limit** -- the best edge is **4555 DN = 60.0%** of the "
     "p1-p99 range. **And it is the subject, not the fitter:** a synthetic sigma=1.2 edge injected at the "
     "real DN range **through the identical code path** returns MTF50 0.1556 against an analytic 0.1562 "
     "(**-0.4%**), angle recovered +5.00 deg.",
     "**The near-0 deg readings of 0.005-0.018 c/px are ALIASING ARTEFACTS and must never be quoted as "
     "sharpness** -- with no slant there is no phase diversity across rows, the projected ESF is "
     "undersampled, and the values sit 5-20x below anything this rig can optically achieve. The single "
     "\"plausible\" slanted candidate was also discarded on its own evidence: NOALIGN 0.0727 / REAL "
     "0.0070 / ZOOM 0.0090 is a **10x swing that is physically impossible between those arms**, with the "
     "fitted angle sliding +6.59 -> +3.94 deg, i.e. the ROI losing its edge. **Nothing in code unblocks "
     "this; the fix is a capture that is already requested** -- `captures-needed.md` §19 already "
     "specifies a backlit razor edge filling >=800 px, **tilted 3-7 deg**, at three apertures with the "
     "rig untouched, and that one capture feeds both this instrument and M88's cutoff instrument.",
     "M104c-verify, 4 bars pre-registered; ORCH reproduced V1-V3 byte-identically from the committed "
     "copy at `experiments/M104c-mtf/mtf.py` (MEASURED)"),

    (1441,
     "**COMPARING A ZOOMED ARM AGAINST AN UNZOOMED ARM CARRIES A MAGNIFICATION BIAS THAT READS AS "
     "SHARPNESS: 0.65% IN MTF50, AND ~16 px OF CONTENT DISPLACEMENT AT THE FRAME EDGE.** `REAL` and "
     "`ZOOM` are scaled by *field of view scaled to 0.9935*; `NOALIGN` is not. In cycles/pixel that is a "
     "**0.65% systematic favouring the unzoomed arm**, and at 2480 px off-centre it translates content by "
     "**~16 px** -- enough to move an edge out of a fixed 160-px ROI entirely, which is exactly what "
     "produced the discarded 10x swing in fact 1440.",
     "**This is the same class of error as the `b843a3f` bug -- apparent magnification reading as "
     "sharpness -- and it now has a second, independent instance**, so it should be treated as a "
     "recurring hazard of this codebase rather than a one-off. Any future cross-arm comparison must "
     "correct by 0.9935 **and re-locate the edge per arm**, not merely reuse ROI coordinates. Note this "
     "does not retroactively damage fact 1439's `+2.73%`: there the FOV change was part of the quantity "
     "being priced (\"resample+FOV cost\"), not an uncontrolled confound. **Confirmed fixed in the same "
     "run:** `STREHL_WARPMAP` + `STREHL_ALIGN=zoom` compose correctly and left **0 sidecars** in the "
     "stack directory, closing the MEDIUM pollution defect of fact 1436.",
     "M104c-verify (MEASURED)"),

    (1442,
     "**I COMMISSIONED AN INSTRUMENT THAT ALREADY EXISTED, HOURS AFTER FOLDING THE DISCIPLINE THAT "
     "FORBIDS IT.** My assignment to M104c asserted the project \"has no sharpness instrument that "
     "survives your critique\" and told it to build a slanted-edge MTF. Both halves were already false in "
     "the repository: `experiments/M88-optical-ceiling/src/` holds a **14-stage, pre-registered, "
     "calibrated ISO-12233 slanted-edge SFR estimator** whose `PREREGISTRATION.md` says so verbatim, and "
     "`docs/captures-needed.md` §19 opens by stating that **M88 built it and could not use it**, then "
     "specifies the 3-7 deg tilt that would fix it. **Discipline 716 -- \"before building a control, grep "
     "for one\" -- was folded by me the same night, after making this error once already.**",
     "**The corpus's disciplines are not self-enforcing, and an orchestrator with a large context is the "
     "most likely agent to violate them**, because it writes briefs from memory rather than from the "
     "tree. The concrete rule this yields: **never assert \"the project has no X\" in a brief without "
     "grepping `experiments/`, `docs/research/` and `captures-needed.md` for X first** -- an unchecked "
     "capability claim in a brief is an instruction to duplicate work. Salvage, honestly stated: this is "
     "an **independent reimplementation reaching the same negative verdict on the same stack**, validated "
     "by different means, so it is a genuine replication of M88's negative -- worth less than the cycle "
     "it cost, but not nothing.",
     "ORCH, verified against `experiments/M88-optical-ceiling/` and `captures-needed.md` §19 (MEASURED)"),
]

DISCIPLINES = [
    (722,
     "**To tell a broken instrument from an unusable subject, inject a synthetic signal at the real data's "
     "scale through the identical code path.** M104c's fitter accepted 0 of 103 real ROIs; the question "
     "\"is my fitter broken?\" was then settled in one command by pushing a synthetic sigma=1.2 edge, "
     "**at the real DN range**, through the same function -- it returned -0.4% against analytic. Without "
     "that probe the honest report is \"no result\"; with it the report is \"the photograph cannot answer "
     "this\", which is actionable and became a capture request. **A zero-accept rate is never "
     "self-explaining.** Fact 1440."),
    (723,
     "**\"Machine built, no fuel\" is a legitimate and reportable milestone outcome -- do not force a "
     "number out of a subject that cannot supply one.** Two independent milestones have now built "
     "validated slanted-edge instruments that no capture in the corpus can exercise. The wrong response "
     "is to quote the near-0 deg readings; they are aliasing artefacts 5-20x below optical possibility "
     "and would have entered the corpus as sharpness. The right response is what both did: state the "
     "instrument passes, state the subject fails, and name the capture that unblocks it. Facts 1440, "
     "1442."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1439 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^721\. ", l))
    assert disc_idx > fact_idx

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        k = r.count("|") - r.count("\\|")
        assert k == 5, f"fact {fid}: {k} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(r)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("folded facts 1440-1442, disciplines 722-723")


if __name__ == "__main__":
    main()
