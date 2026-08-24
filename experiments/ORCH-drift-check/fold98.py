"""Fold M112: the crop NO-GO, the 8-frame provenance defect, and redundant causation."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1459,
     "**STOPPING THE OUTPUT ENLARGEMENT RECOVERS NOTHING: MEASURED −0.0030 dex, THE WRONG SIGN.** "
     "Pre-registered NO-GO, phases 1 and 2 correctly not built. `fit_to_cover` returns **one composed "
     "mapping and one gather**, so dropping the scale factor moves the sampling step from `0.931464` to "
     "**1.0014 — still non-integer**, still paying nearly the full price. **8 of 9 stacks dead.** "
     "`foam` carries the **largest** enlargement (**14.14 %**) and the **most negative** recovery; the "
     "single exception has the **smallest** (**0.30 %**) and recovers **+0.1516**. The reference frame "
     "in isolation does go from **+0.1836 dex** of loss to **−0.0000** without the scale -- real waste, "
     "correctly identified -- and it is worth **1 frame in 299**.",
     "**The argument that sent this milestone was mine, it was sound, and it was worth nothing "
     "measurable.** A per-frame waste that is real and a stack-level gain that is absent are perfectly "
     "compatible, and only measurement separates them. Note the gate *could* have fired -- the lone "
     "exception recovers a large positive -- so this is a discharged risk rather than an instrument too "
     "blunt to respond. **The registered stopping rule is what makes the negative cheap: two further "
     "phases were never built.**",
     "M112-real-pixels, pre-registered `386ee63` before any arm ran"),
    (1460,
     "**FACT 1419'S NUMBERS -- AND THE \"9.4x\" MULTIPLIER DERIVED FROM THEM -- WERE MEASURED ON AN "
     "8-FRAME QUARANTINED SIDECAR, NOT ON THE SHIPPED 299-FRAME SOLVE.** Fact 1419's five published "
     "quantities reproduce **digit for digit** against a quarantined 8-frame / reference-4 sidecar "
     "(`stack-digest 165a1ff35968c615`) and **not** against the 299-frame solve "
     "(`stack-digest 8d023c0fe355d109`) that every corpus quality number uses; the two digests differ, "
     "so these are not two copies of one solve. The multiplier in fact 1420 is "
     "`0.1343 / 0.0143 = 9.392`, and that denominator is `fix_recovery_dex` from `x8_fix.json` -- **the "
     "8-frame file.** On the shipped solve the same quantity is **−0.0030**.",
     "**You cannot divide by a quantity of the opposite sign and obtain a multiplier, so the \"9.4x\" is "
     "not a ratio -- it is an artefact of comparing two different stacks.** The correct statement is "
     "**`+0.1343` against `−0.0030`**, which makes the conclusion *stronger* than the retracted form: "
     "the kernel is not 9.4 times a positive term, it is a positive term against a term that does not "
     "exist. **I used that multiplier all night to re-prioritise three agents.** The generalisable "
     "defect is provenance, not arithmetic: **a sidecar is an input, and a folded result that does not "
     "record its sidecar's frame count and `stack-digest` is not a record** -- `x8_fix.py` wrote "
     "neither, two hours after rule 47 was written. Every quality number in this corpus should be "
     "checkable against the solve it was measured on.",
     "M112-real-pixels section 9.2, amending facts 1419 and 1420"),
    (1461,
     "**THE RESCALE IS A SUFFICIENT BUT REDUNDANT CAUSE OF THE SHARPNESS LOSS, WHICH IS WHY REMOVING IT "
     "RECOVERS NOTHING.** In isolation the rescale costs the **full** price -- the reference frame alone "
     "goes **+0.1836 to −0.0000**, and one stack recovers **+0.1516** at stack scale. Yet removing it "
     "across the shipped stack recovers **−0.0030**, because **99.7 % of `bee-3-cpl`'s frames are "
     "already non-integral without it.** The effect **saturates**: a second sufficient cause of the same "
     "damage is already present in almost every frame.",
     "**This dissolves the fact 1287 / fact 1420 tension with neither fact wrong, and it retires a "
     "number that has been cited repeatedly. Fact 1287's share of the deficit is an ATTRIBUTION, not a "
     "BUDGET** -- under redundant causation the attributed shares sum past 100 %, because *remove the "
     "scale* and *remove the warp* each return most of the deficit in isolation. **That share is not "
     "recoverable by anyone, and it is the number that sent this milestone.** The kernel is the lever "
     "for a structural reason rather than a numerical one: **it is the only term acting on the *price* "
     "of non-integer phase rather than on a *cause* of it, and phase is irreducible** -- 299 hand-held "
     "frames cannot land on integer offsets. **Falsifiable prediction, handed over untested: the kernel "
     "gain should be roughly stack-independent, whereas the crop's recovery ranges −0.0330 to +0.1516 "
     "across nine stacks.** Running the kernel arm across those nine settles it in one pass.",
     "M112-real-pixels section 9.4, labelled DERIVED/ARGUED by its author; prediction untested"),
]

DISCIPLINES = [
    (745,
     "**A null must be checked for being maximally DIFFERENT from the arm, not only for being nominally "
     "equal to it.** I prescribed a null in which an identity sidecar was resampled at `k = 1.0` against "
     "the arm's `k = 0.9974`. **On an identity sidecar `k = 1.0` is an exact no-op while `k = 0.9974` "
     "is a full non-integer resample**, so the two are as far apart as the experiment can make them: it "
     "fires at **+0.1851 dex** and would have voided a correct measurement as contaminated. M112 "
     "identified this **in advance**, registered the substitution, and used a null whose true value is "
     "**zero by construction**. The general trap: **a null designed by varying a parameter can "
     "accidentally straddle a discontinuity in what that parameter means** -- here, integer versus "
     "non-integer sampling -- so the parameter looks like a small change while the operation is a total "
     "one. **Prefer nulls whose expected value is zero by construction over nulls that are merely "
     "expected to be small.** Note the direction of the damage: this null fails *loudly*, condemning "
     "good work, where discipline 738's failed *silently*, blessing bad."),
    (746,
     "**Revising a pre-registered bar before data is legitimate; after data it is not -- and the "
     "difference is visible in git history.** I sent M112 a recalibration inviting it to re-register a "
     "more defensible bar. It arrived **after** Phase 0 had resolved, and M112 **refused**: it left "
     "`PRE-REGISTRATION.md` byte-unchanged at its original commit and answered on the merits instead, "
     "pointing out that the measured recovery was **negative** and that **no bar admits a wrong sign** "
     "-- not even the one my own decomposition implied. **An orchestrator offering to relax a bar is a "
     "pressure on the result whether or not it is intended as one**, and the correct response to it is "
     "the one M112 gave. Pre-registration only means anything if the file's history is the record and "
     "the author defends it against the person who commissioned the work."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1458 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^744\. ", l))
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
    print("folded facts 1459-1461, disciplines 745-746")


if __name__ == "__main__":
    main()
