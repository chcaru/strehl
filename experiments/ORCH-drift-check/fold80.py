"""Fold the magenta highlight defect. Facts 1432-1434, disciplines 713-714."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1432, "**STREHL RENDERS BLOWN HIGHLIGHTS MAGENTA WHERE THE SCENE IS NEUTRAL WHITE, ACROSS 2.002% OF A "
           "33 MP RENDER.** On `dry-erase-marker-head-cpl` at HEAD `8f46f04` (`--srgb --auto-exposure "
           "--gate 4`, exposure chosen `-0.24`), pixels satisfying `R-G>0.06 && B-G>0.06` mean "
           "`R=0.9944 G=0.8915 B=0.9943`, `max(R-G)=0.4490`, in one large contiguous blob centred at "
           "(0.967, 0.434) of frame plus coloured fringing along specular edges. **Mechanism confirmed against "
           "a registered prediction**: in the affected region of `DSC00150.ARW` both green channels sit at "
           "**100.00% of saturation** (`G1=G2=16383.0`, white level 16383) while **R is at 7673.2 and B at "
           "14116.0, neither saturated at all**. Camera WB is `R x2.687, G x1.0, B x1.532`, so green is pinned "
           "at its ceiling while white balance scales R and B up past it. A neutral white reference region on "
           "the same frame has no channel near saturation (R 2569, G 5865, B 3937). **LibRaw renders the same "
           "region pure neutral white.**",
     "**Per-channel highlight clipping, which every mature RAW pipeline handles and strehl does not.** "
     "`clip.rs` already detects samples pinned at `CONTAINER_MAX_DN` and feeds a `ClipCensus`, but that serves "
     "the **focus** path -- a clipped sample is not a focus measurement -- and **nothing carries the "
     "consequence into the colour path**. White balance and the colour matrix are applied to values with one "
     "channel pinned, with no desaturation or reconstruction. This is grossly visible and is part of what the "
     "owner was reacting to. Assigned to M109 as a **viewing-path-only** fix: the byte-frozen measurement "
     "output must not move, and an unsaturated stack must be byte-identical after it.",
     "ORCH `pink_probe2.py`, registered prediction confirmed (MEASURED); rawpy/LibRaw cross-check (MEASURED)"),

    (1434, "**MY FIRST COLOUR PROBE MEASURED THE WRONG REGION AND CLEARED THE DEFECT.** I sampled an ROI at "
           "x 0.80-0.95 of frame and reported strehl and LibRaw agreeing to **0.2% on redness** (pinkness "
           "0.9666 vs 0.9645) -- a true statement about that ROI and a false conclusion about the render. The "
           "blob's centroid is at **x = 0.967**; my ROI sat mostly on the white pipe and diluted it away. The "
           "defect was found instead by looking at a **downscaled view of the whole frame**, and only then "
           "located precisely by letting the data choose the region (`argwhere` on the magenta predicate) "
           "rather than choosing it myself.",
     "**A targeted statistic inherits every error in the targeting, and averaging over a hand-drawn ROI is "
     "the most efficient way to hide a localised defect.** I picked the ROI from an impression of a "
     "thumbnail, which is exactly the kind of unrecorded judgement call this project bans elsewhere. The "
     "cheap general defence: **look at the whole image first, then let the predicate locate the region and "
     "report its bounding box and centroid** -- which also yields the extent for free and cannot be "
     "mis-aimed. Related to but distinct from discipline 24's flat-ROI placebo: that guards against a control "
     "region being unrepresentative; this guards against the *measurement* region missing the effect.",
     "ORCH `pink_probe.py` (cleared it) vs `pink_probe2.py` (located it at x=0.967) (MEASURED)"),

    (1433, "**THE MONTAGE'S OWN CORRELATION BAR REFUSED TO PUBLISH THE `marker` COMPARISON, AND IT WAS RIGHT "
           "TO.** `then_vs_now_all.py` registers `R1: correlation peak > 0.5` before running. `bee3` and "
           "`lavendar` passed at 0.8612 and 0.9016; **`marker` reached only 0.2464 across four probes and the "
           "run aborted.** Cause, found by inspection rather than by relaxing the bar: the judged render is "
           "unaligned while HEAD applies the ~7-10% alignment FOV crop, so the two differ by a **scale "
           "change**, and no rigid integer offset can register them. On `bee3`/`lavendar` a large patch still "
           "correlated through the scale mismatch; on `marker` the subject is large and smooth, so the "
           "mismatch dominates.",
     "**A bar that fails for a reason you did not anticipate has just done its job** (discipline 710, second "
     "instance in one session). Relaxing R1 to 0.2 would have published a montage whose two panels show "
     "different parts of the subject, which is worse than publishing nothing -- it is a fabricated "
     "comparison. The correct response was to present `marker` as a whole-frame comparison, where the defect "
     "that matters there is a large-scale colour feature anyway and needs no registration.",
     "ORCH `then_vs_now_all.py` R1, 3 stacks (MEASURED)"),
]

DISCIPLINES = [
    (713, "**Look at the whole image before trusting a number computed on part of it.** A hand-placed ROI "
          "inherits every error in its placement, and averaging is the most efficient way to dilute a "
          "localised defect to nothing -- my ROI cleared a 2.002% magenta blob to a 0.2% agreement with "
          "LibRaw. **Let the predicate find the region**: threshold, then report the bounding box, centroid "
          "and extent from the data. It cannot be mis-aimed and it gives the extent for free. Facts 1432, "
          "1434."),
    (714, "**Before publishing a before/after comparison, make it prove the two sides show the same thing.** "
          "Register a correlation floor and let it abort the montage. `then_vs_now_all.py`'s R1 caught that "
          "the judged and current `marker` renders cannot be rigidly registered at all, because alignment's "
          "FOV crop makes the difference a scale change rather than a translation. Without the bar the "
          "montage would have rendered anyway, silently comparing two different parts of the subject. Fact "
          "1433."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1431 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^712\. ", l))
    assert disc_idx > fact_idx, "discipline list must follow the fact table"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        n = r.count("|") - r.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes"
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
    print(f"folded facts 1432-1434, disciplines 713-714")


if __name__ == "__main__":
    main()
