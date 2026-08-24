"""Fold the defect-audit result and the control that killed most of it."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1438,
     "**AN ARTEFACT AUDIT WITHOUT AN UNSTACKED CONTROL IS MOSTLY MEASURING THE SCENE: A CONTROL KILLED "
     "3 OF 5 \"DEFECTS\" I FOUND.** An 8-check battery with thresholds registered before the run was put "
     "over the two HEAD renders (`lavendar-cpl`, `dry-erase-marker-head-cpl`, 7040x4688) and reported "
     "five FIRED. The identical battery over a **single unstacked LibRaw frame of the same scene** "
     "(middle frame, camera WB, no auto-bright, sRGB) then refuted three of them. **Killed:** the "
     "waxy-blob check (control **8.3%/10.1%** against strehl's 10.2%/**6.8%** -- **on `marker` the "
     "control is HIGHER than strehl**); the banding check (control **6483x/17518x** peak-to-median, same "
     "order as strehl -- it reads ordinary vignetting and subject gradient); and the overshoot check, "
     "which returned **147% and 150%**, impossible for a fraction, because its numerator uses a dilated "
     "edge mask and its denominator the undilated one. **Survived:** magenta at **2.0017% vs control "
     "0.0061%** (a **328x** excess) and edge chroma on `lavendar` at **4.22x vs control 1.36x** (a 3.1x "
     "excess), the latter **localised** -- `marker` is 2.65x against a control of 2.23x, essentially all "
     "scene.",
     "**The magenta defect is now control-backed and its cause narrowed: LibRaw sees the same saturated "
     "sensels and does not render them magenta**, so the fault is in strehl's colour path rather than in "
     "the capture -- which is what M109 was dispatched to fix, now with the control that dispatch "
     "lacked. The chroma finding corroborates M107 and adds something M107 did not have: it is "
     "scene-dependent, not global, so a fix must be validated on `lavendar` and must not regress "
     "`marker` where there is nearly nothing to remove. **The wider lesson is the failure rate: three of "
     "five candidate defects were phantoms, and all three would have become dispatched milestones.** "
     "Checks built from percentiles of the image under test fire on any image by construction. **The "
     "waxy blobs remain WITHOUT AN INSTRUMENT** -- the check aimed at them was the first one the control "
     "refuted, so their absence from this audit is not evidence about them.",
     "ORCH `defect_audit.py` + `single_frame_control.py`, 8 checks x 2 renders x 2 controls (MEASURED)"),
]

DISCIPLINES = [
    (718,
     "**An output-artefact audit needs an unstacked single frame of the SAME scene as its control, and "
     "the control must be run before any finding is dispatched.** Without it there is no way to separate "
     "\"strehl produced this\" from \"this is what the subject looks like\", and the separation is not "
     "guessable: one check had the control scoring *worse* than the product. Develop the middle frame "
     "through LibRaw with camera WB and no auto-bright, run the identical battery, and report every "
     "number as a ratio to its control. Fact 1438."),
    (719,
     "**A metric that can exceed its own logical range is not a weak metric, it is a broken one -- stop "
     "and find the defect rather than ranking with it.** The overshoot check returned 147%, and a "
     "fraction cannot exceed 100%: numerator and denominator had different supports. Had it returned a "
     "plausible 14.7% the same bug would have been invisible and the number would have been folded. "
     "**Range-check every ratio metric against its definition before reading it**, and treat an "
     "out-of-range value as information about the instrument, never as a large effect. Fact 1438."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1437 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^717\. ", l))
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
    print("folded fact 1438, disciplines 718-719")


if __name__ == "__main__":
    main()
