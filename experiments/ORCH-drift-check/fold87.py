"""Fold the waxy-blob measurement: flat interior + hard boundary, against a control."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1444,
     "**THE DEFECT THE OWNER CAN SEE HAS A SIGNATURE AND A CONTROL: THE MERGE SYNTHESISES PALE PATCHES "
     "WHOSE INTERIOR IS 10.6x FLATTER THAN THEIR OWN SURROUNDINGS AND WHOSE BOUNDARY IS 6.1x HARDER THAN "
     "THE SAME REGION IN A SINGLE FRAME.** Merged render at `8f46f04` vs a middle frame through LibRaw "
     "with camera WB and no auto-bright, both 4688x7028. On `marker` at `(2048,1300)`: gradient energy "
     "inside-patch / outside-patch is **0.094 in the merged arm against 0.761 in the control**, and "
     "boundary gradient p90 is **1384.04 merged against 226.69 control**. **Exposure is not the "
     "mechanism** -- global luma means are 31665.6 vs 32378.0, ratio **0.978**. Visually the patches are "
     "internally featureless with hard scalloped polygon-like edges, where the control shows a smooth "
     "featureless defocused gradient: **the merge is inventing structure present in no input frame.**",
     "**Flat interior plus hard boundary is the \"waxy\" look, and it is now measurable rather than "
     "merely complained about.** This is the first instrument for this defect; `defect_audit.py`'s D3 "
     "attempt was killed by its own control (fact 1438), and this one survives the same control. **A "
     "second, weaker patch at `(4715,1180)` shows the anomalous boundary (737 vs 237) but NOT the "
     "anomalous interior (1.477 vs 1.468), so the two are separable and any proposed mechanism must say "
     "which it explains.** Mechanism is **UNMEASURED** and dispatched as M111 with two pre-registered "
     "hypotheses: regulariser plateaus at `REGULARISER_RADIUS` 8, and the fact 19 noise-gated mean "
     "failing to fire where no frame is better than any other. **If the regulariser hypothesis holds it "
     "is uncomfortable rather than convenient: fact 84 prices that regulariser at -35% absolute error, "
     "so the component improving our error metric would be causing our worst visible artifact.**",
     "ORCH, `experiments/ORCH-drift-check/blob_probe.py` + `look_defects.py` against "
     "`single_frame_control.py` (MEASURED)"),
]

DISCIPLINES = [
    (726,
     "**When comparing two arms as images, a single shared stretch can render one arm unreadable -- "
     "stretch per arm and report the brightness difference as a NUMBER.** My first contact sheet used one "
     "shared percentile stretch for both arms, reasoning that a per-arm stretch would let a brightness "
     "difference masquerade as a structural one. On `lavendar` that choice rendered the control arm "
     "**pure black**, and the comparison it existed to make was impossible. The fix keeps the original "
     "concern satisfied without the blindness: stretch each arm to its own percentiles so both are "
     "legible, and print the luma-mean ratio (0.978 on `marker`) so the brightness question is answered "
     "explicitly instead of implicitly. Fact 1444."),
    (727,
     "**Look at the output before commissioning another metric for it.** This defect had been described "
     "by the owner in plain words, had survived one failed scoring attempt, and had no owner -- and it "
     "took one contact sheet and one 60-line probe to find, measure and localise, after many hours of "
     "metrology on quantities that change no pixel tonight. The corpus's measure-before-build discipline "
     "is right, but it does not license measuring things nobody is looking at while the visible defect "
     "goes uninstrumented. Fact 1444."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1443 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^725\. ", l))
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
    print("folded fact 1444, disciplines 726-727")


if __name__ == "__main__":
    main()
