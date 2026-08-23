"""Fold M25 (the calibrated simulator / digital twin) into SYNTHESIS.md.

NUMBERING (rule 28). M25's report proposes facts 190-200, disciplines 100-107
and questions 30-35. All three blocks are taken: facts 200-203/210-213/220-225
belong to M20-V and later milestones, disciplines run to 267, questions to 110.
Per rule 25 the whole blocks are shifted to open ground rather than interleaved:

    facts        190-200  ->  540-550
    disciplines  100-107  ->  268-275
    questions     30-35   ->  111-116

The mapping is ordinal in every case. Recorded here and in the report.

Claim cells are parsed from the report rather than retyped, so the author's
wording is preserved verbatim; only the leading "**N. LABEL.**" is stripped and
newlines collapsed. The Consequence column is the orchestrator's synthesis and
is written here.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
DOC = "M25-simulator-measured.md"
RPT = pathlib.Path("docs/research") / DOC

FACT_MAP = {190 + i: 540 + i for i in range(11)}
ANCHOR = "| 511 |"

CONSEQUENCE = {
    540: "**The digital twin is real for the selection machinery, and this is the strongest independent confirmation fact 35 has.** A mechanism inferred from two real stacks now emerges from calibrated constants alone, and the zero-centre-tap arm is the placebo proving the plant can express its own absence. The external review's item 5 (\"the calibrated simulator compounds everything else\") is **partially delivered — for noise and selection only**, per fact 544.",
    541: "**The decomposition localises the simulator's error to exactly one term.** Selection is trusted to sub-1%; the floor is not. Every use of the twin must therefore quote noise-*excess* results and withhold absolute noise *levels*.",
    542: "**A systematic, sign-stable offset in the one term the merge cannot remove** — the signature of an unmodelled fixed-pattern component rather than a tuning error. Question 111 (PRNU) is the leading suspect and is blocked on the flat-field capture already scheduled in `captures-needed.md`.",
    543: "**The twin cannot be tuned to match selection and averaging at the same time**, so one free parameter is standing in for a structural difference. Never report a simulated headline tuned on one axis and read on another; fact 543 is the reason gate 1b is `PARTIAL` and not `PASS`.",
    544: "**The single most important limitation in the report, and it disqualifies the twin from the job the external review assigned it.** The review proposed the simulator as ground truth for the deconvolution work; a validation suite that cannot detect *deleting the PSF entirely* cannot score a PSF-inversion method. M19's kill experiment must keep its real-data arms, and question 114 asks what gate would actually bite.",
    545: "**Independent confirmation of fact 35 by a route that never touches φ** — and a warning with teeth: any stage that correlates noise (demosaic, resample, denoise) *shrinks* the very defect the merge exists to remove and will therefore flatter it. Measure the defect pre-resample, in the CFA domain, or measure it smaller than it is.",
    546: "**Every synthetic plant in this corpus built on a single `f^-β` is mis-shaped at exactly the frequencies focus measures read.** Discipline 273 makes the two-band fit mandatory. This is also a partial mechanism for gate 1c's failure, since the occlusion detector of fact 548 keys on fine-scale structure the single-β plant over-supplies.",
    547: "**Fourth independent confirmation that this corpus's \"flat\" ROIs carry real structure**, joining fact 455, which killed `SELECTION_INFLATION`. The harness's reference frame is not the sharpest frame on its own ROI, so every ratio taken against it has a defocused denominator. Discipline 268 generalises the rule.",
    548: "**M21's occlusion detector does not survive transplant to a plant whose ground truth is known.** Enrichment *inverts* — 0.77x against a real 4.38x — while the permutation placebo stays honest at 0.99, so this is the detector failing rather than the harness. Fact 150's mechanism may still be real, but its detector is not portable and the occlusion-reconstruction workstream cannot be built on it as it stands.",
    549: "**Compositing order is a first-order modelling decision, not a refinement.** Any two-layer occlusion model must state which order it assumes and match the physical one, or it injects an error of the same magnitude as the halo it exists to remove.",
    550: "**A shipped noise-model constant is wrong at the bottom of the ISO range, and ISO 50 is exactly where a tripod macro stack is shot.** The merge gate is denominated in this sigma, so at ISO 50 the pipeline believes a noise floor roughly half the real one. Re-fit the read-noise term with an explicit low-ISO branch before any ISO-50 result is trusted; note the error is non-monotone (2.6% at ISO 160), so a two-level model is the wrong shape, not merely the wrong constant.",
}

DISCIPLINES = [
    (268, "**A synthetic plant must not be placed at a fixed point of the harness measuring it.** Placing a plane's best focus on the frame the harness divides by pins the merged/single ratio at 1.000 by construction. Extends discipline 24: the leak need not be *into* the plant. (M25 §5.1; facts 540, 547.)"),
    (269, "**Before comparing a simulated statistic against a committed number, reproduce the REGIME the number was measured in** — contrast, ISO, structure-to-noise — not merely its harness. Across this corpus the same detector reads **4.8%** and **60.7%** on two real stacks. (M25 §5.2; fact 548.)"),
    (270, "**If a gate is changed after seeing which axis failed, the original gate must still be run and reported.** Report the post-hoc version separately and label it post-hoc *wherever it appears*. M25 did this for gate 1b' and said so in its own headline table. (M25 §5.3.)"),
    (271, "**A negative control on a simulator must mis-specify the physics AND re-calibrate the summary statistics back onto the real values.** A mis-specification that moves the mean or sd is caught trivially and proves nothing about the gate's power. (M25 §4.4; fact 544.)"),
    (272, "**When a negative control does not fire, determine whether the knob is a no-op before concluding the gate is insensitive.** The two have opposite implications and the check costs one render. (M25 §4.4.)"),
    (273, "**A calibration probe rendered below the quantisation floor measures rounding, not signal**, and a subject spectrum fitted on one sub-band must not be extrapolated to another: an optical chain reddens the spectrum again, so fine-scale content is starved twice. Fit the two bands separately. (M25 §5.6, §5.7; fact 546.)"),
    (274, "**State the fitted-versus-tested split as a table before presenting any simulated result, and state the COUNT of fitted numbers.** \"β\" and \"a 64-bin radial profile\" are different claims about how much of reality was assumed. (M25 §2.)"),
    (275, "**A simulator's usable domain is the set of axes its own negative control can see.** M25's fires on gain, noise correlation and noise absence, and is blind to deleting the PSF — so the twin is evidence about noise and selection and is *not* evidence about optics, however physically its optics were written. Publish the blind axes next to the passing gates. (M25 §0, §4.4, §6; fact 544.)"),
]

QUESTIONS = [
    (111, "**What accounts for the 0.03-0.05 merged-noise floor deficit (fact 542)?** PRNU is the leading suspect and is unmeasured. The flat-field capture already listed in `docs/captures-needed.md` would settle it. Until then the twin's absolute noise levels are not quotable."),
    (112, "**Would a real-texture latent scene — a high-resolution photograph of an organic subject used as `L` — close the gate 1c gap?** The simulator supports it; the corpus does not yet contain a suitable high-magnification flat capture."),
    (113, "**Why does the fitted `coc_px_per_frame` run to the grid edge on `coffee-bean` (12.0 px/frame, RMS shape error 0.17) but sit comfortably at 1.5 on 109MSDCF?** Is real defocus growth non-linear in frame index, or is the subject's depth range doing the work? Bears directly on whether the focus axis can be treated as uniformly sampled."),
    (114, "**What gate would be sensitive to the PSF?** Fact 544 says none of the current ones are. Candidates M25 names: through-focus MTF against M5's measured aperture sweep; the through-focus curve *shape* (real curves are asymmetric and fall faster than any simulated one at `coffee-bean`); edge-spread reconstruction against a real razor edge. **This question gates every optical use of the simulator.**"),
    (115, "**Does the excess deficit at wide support (`ring-4-12`: 0.022 vs 0.115) share a cause with the floor deficit of fact 542, or is it a separate mismatch in how correlated the real focus field is at long range?**"),
    (116, "**Is the simulated speckle excess (50.3% vs 38.2%) fully explained by the subject-spectrum mismatch of fact 546, or does it survive spectrum shaping?**"),
]


def esc(s):
    return re.sub(r"(?<!\\)\|", r"\\|", s)


def parse_facts():
    text = RPT.read_text(encoding="utf-8")
    seg = re.search(r"^## 7\..*?$(.*?)^## 8\.", text, re.M | re.S)
    if not seg:
        raise SystemExit("M25 section 7 not found")
    body = seg.group(1)
    parts = re.split(r"^\*\*(\d+)\.\s", body, flags=re.M)
    out = {}
    for i in range(1, len(parts), 2):
        n = int(parts[i])
        if n not in FACT_MAP:
            continue
        claim = " ".join(parts[i + 1].split())
        claim = claim.rstrip("-").strip()
        if claim.endswith("---"):
            claim = claim[:-3].strip()
        m = re.match(r"^([A-Z][A-Z ]+)\.\*\*\s*(.*)$", claim)
        if not m:
            raise SystemExit(f"fact {n}: cannot split label from '{claim[:60]}'")
        out[n] = (m.group(1).strip(), m.group(2).strip())
    if sorted(out) != sorted(FACT_MAP):
        raise SystemExit(f"expected {sorted(FACT_MAP)}, parsed {sorted(out)}")
    return out


def main():
    facts = parse_facts()
    text = SRC.read_text(encoding="utf-8")

    present = {int(m) for m in re.findall(r"^\| (\d+) \|", text, re.M)}
    new = set(FACT_MAP.values())
    if present & new:
        raise SystemExit(f"fact collision: {sorted(present & new)}")

    # Rule 28: content check. None of these claims may already be in the table.
    for src, dst in FACT_MAP.items():
        probe = facts[src][1][:60]
        if probe and probe in text:
            raise SystemExit(f"fact {src} already folded (content match) - refusing")

    d5 = re.search(r"^## 5\.", text, re.M)
    d5e = re.search(r"^## ", text[d5.end():], re.M)
    dseg = text[d5.start(): d5.end() + d5e.start()]
    dpresent = {int(x) for x in re.findall(r"^(\d+)\. \*\*", dseg, re.M)}
    if dpresent & {n for n, _ in DISCIPLINES}:
        raise SystemExit(f"discipline collision: {sorted(dpresent & {n for n, _ in DISCIPLINES})}")

    q10 = re.search(r"^## 10\.", text, re.M)
    qpresent = {int(x) for x in re.findall(r"^(\d+)\. \*\*", text[q10.start():], re.M)}
    if qpresent & {n for n, _ in QUESTIONS}:
        raise SystemExit(f"question collision: {sorted(qpresent & {n for n, _ in QUESTIONS})}")

    rows = []
    for src in sorted(FACT_MAP):
        dst = FACT_MAP[src]
        label, claim = facts[src]
        prov = f"M25 §7 fact {src} (renumbered {dst}; see [`{DOC}`]({DOC})) — **{label}**"
        row = f"| {dst} | {esc(claim)} | {CONSEQUENCE[dst]} | {prov} |"
        if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
            raise SystemExit(f"row {dst}: unescaped pipe")
        rows.append(row)

    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith(ANCHOR)]
    if len(idx) != 1:
        raise SystemExit(f"anchor {ANCHOR!r} not unique ({len(idx)})")
    lines[idx[0] + 1: idx[0] + 1] = rows
    text = "\n".join(lines)

    d5 = re.search(r"^## 5\.", text, re.M)
    d5e = re.search(r"^## ", text[d5.end():], re.M)
    lo, hi = d5.start(), d5.end() + d5e.start()
    seg = text[lo:hi]
    m = re.search(r"^267\. \*\*", seg, re.M)
    if not m:
        raise SystemExit("discipline 267 not found")
    nxt = re.search(r"^\d+\. \*\*", seg[m.end():], re.M)
    ins = lo + (m.end() + nxt.start() if nxt else len(seg.rstrip("\n")) + 1)
    text = text[:ins] + "".join(f"{n}. {d}\n\n" for n, d in DISCIPLINES) + text[ins:]

    text = text.rstrip("\n") + "\n\n" + "".join(f"{n}. {q}\n\n" for n, q in QUESTIONS)

    SRC.write_text(text, encoding="utf-8")
    print(f"facts {sorted(FACT_MAP.values())}")
    print(f"disciplines {[n for n, _ in DISCIPLINES]}")
    print(f"questions {[n for n, _ in QUESTIONS]}")


if __name__ == "__main__":
    main()
