"""Fold M109-highlights: the magenta defect in the shipped default, and two disciplines."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1455,
     "**THE SHIPPED DEFAULT RENDERS BLOWN HIGHLIGHTS MAGENTA, AND THE MECHANISM IS A CLAMP IN THE WRONG "
     "PLACE.** `strehl stack` on `marker`: **2.0017 %** of frame magenta by the R−G predicate, "
     "**max(R−G) = 0.4490**, channel means **0.9944 / 0.8915 / 0.9943** — green pinned **0.10 below** red "
     "and blue, where a blown highlight must be neutral. Render order, **read from source rather than "
     "assumed**: `strehl stack` goes through `merge_cmd::write_merged` (**not** `stack.rs`, which serves "
     "`argmax-baseline`); black, as-shot green-normalised WB, exposure gain, demosaic, matrix, "
     "**clamp(0,1)**, sRGB curve, u16. **The only clamp is after the matrix.** M109's fix clips "
     "conditionally *before* the matrix in WB'd camera space at `K0 = (16383−512)/(15360−512) = "
     "**1.0689**`; on `argmax-baseline` magenta falls **0.3378 % to 0.0944 %** with the null "
     "byte-identical (SHA-256 `4B7779AA…`), negative control shown red, byte-freezes **5/5**, workspace "
     "**394 pass / 0 fail**, and a `rawpy`/LibRaw cross-check on **583 873** predicate-selected pinned "
     "quads agreeing to **0.0014**.",
     "**Post-matrix clamping is right for gamut and wrong for a pinned sample, and the two had been "
     "conflated in one line of code.** Once a photosite saturates, its true value is unknown and only "
     "bounded below; clamping after the matrix has already mixed a *known-wrong* green into red and "
     "blue, so no later operation can recover neutrality — the artefact is baked in one step earlier "
     "than the clamp that appears to cause it. The conditional form is what makes the null an identity: "
     "an unconditional clamp at `K` would have clipped genuine red above **~6420 DN** and failed the "
     "byte-identical bar, so **the guard and the fix are the same expression.** This is the defect the "
     "owner was looking at when he said his stacks did not look good; it sat unlanded only because the "
     "file belongs to another agent.",
     "M109-highlights §6, commit `3e58676`; `stack` numbers reproduce ORCH's independent measurement to "
     "4 decimals"),
    (1456,
     "**AUTO-EXPOSURE DOES NOT CAUSE THE MAGENTA DEFECT; IT AMPLIFIES IT 2.8x — MY CLAIM, CORRECTED BY "
     "MEASUREMENT.** I asserted auto-exposure as the cause. M109 measured that at `eg = 1` the same blob "
     "gives **R−G = 0.0371**, which is *below* my own **0.06** detection predicate, while under "
     "auto-exposure it reaches the **2.0017 %** headline.",
     "**So the headline severity was partly a function of gain rather than purely of the colour bug**, "
     "and a fix validated only at auto-exposure would have been credited with more than it earned. The "
     "operational consequence was concrete: `argmax-baseline` had to gain an `--exposure` knob, because "
     "otherwise the baseline and `stack` could only ever be compared **at different gains** — an "
     "uncontrolled variable sitting inside every before/after either produced. **A defect's measured "
     "magnitude is a property of the operating point, not of the defect**, so an amplifier in the path "
     "must be pinned before severity means anything.",
     "M109-highlights, correcting ORCH's causal claim"),
]

DISCIPLINES = [
    (738,
     "**A control that cannot go red is worse than no control, and controls can poison themselves.** "
     "M109's cache-visibility control forced a solve in one arm — **and that arm wrote its warpmap into "
     "the redirect directory**, so on re-run the supposedly cache-blind arm read back its own output, "
     "both arms took the sidecar path, and `A == B` became **vacuous while still printing green**. It "
     "was caught only because the harness carried an explicit **inertness guard** that printed `CONTROL "
     "INERT` and hard-failed. The general shape: **any control with a side effect on the state it "
     "controls for will converge to passing**, and passing is indistinguishable from working. Every "
     "control needs (a) a state reset per arm and (b) an assertion that the perturbation actually "
     "perturbed — M109 evidenced its perturbation from `strehl`'s own stderr, `align=solved` **111 s** "
     "against `align=sidecar` **63 s**. Compare disciplines 730 and 731: the same failure mode, reached "
     "by a different route, for the third time tonight."),
    (739,
     "**When your test set cannot falsify the more aggressive option, ship the conservative one and "
     "register the capture that would decide it.** M109's stricter trigger cleared far more magenta "
     "(**0.0944 % to 0.0260 %**) but touched **6.56 %** of the frame; it changed **0** strongly-coloured "
     "pixels on `marker` and **zero** pixels on `lavendar-cpl`, because *the corpus contains almost no "
     "saturated clipped colour*. **A test set that cannot express a risk will always report that risk as "
     "absent**, and the better-looking number is exactly when that bias is most tempting. The correct "
     "move is neither to ship on unfalsifiable evidence nor to abandon the variant, but to **name the "
     "missing capture and defer the decision to it** — recorded in `docs/captures-needed.md`. "
     "**Distinguish 'measured safe' from 'unmeasurable here' in the report itself**, or a later reader "
     "will read the absence of counter-evidence as evidence."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1454 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^737\. ", l))
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
    print("folded facts 1455-1456, disciplines 738-739")


if __name__ == "__main__":
    main()
