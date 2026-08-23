"""Fold M19 (workstream G, the EDOF/microscopy survey) into SYNTHESIS.md.

Two structural fixes over the first attempt:

  * M19 proposed 120-139, but M20-V already holds 122-139. Shift +280 -> 400-419,
    above every allocated number, so no later fold reasons about a partial overlap.
  * M19's table is `| # | Proposed fact | Label |`; SYNTHESIS is
    `| # | Fact | Consequence | Source |`. The consequence column is the
    orchestrator's to write -- a survey can say what the literature found, not what
    it changes here.

Cross-references are audited, not blind-substituted: "fact 150" inside an M19 row
points at an existing corpus fact and must not move.
"""
import json, re, pathlib

SHIFT = 280
SRC = pathlib.Path("experiments/m19-edof-survey/rows.json")
DST = pathlib.Path("docs/research/SYNTHESIS.md")

CONSEQUENCE = {
    120: "**The novelty claim is withdrawn before it was made.** The review's \"complete the thought\" framing describes 2009 prior art. strehl may implement this estimator and must cite it; it may not claim it",
    121: "**The one crack in the published negative, and the only place a real gain could hide.** Levin's verdict assumes fixed total exposure — each of N frames gets 1/N of the light. A static subject on a tripod does not pay that. Pair with M20's own refutation before acting on either",
    122: "External corroboration of fact 141 from a different modality and a different team. Any inverse filter here must be **regularised by construction, not by option**",
    123: "**Deconvolution degrades the axis where the OTF is weakest, and for a focal stack that axis is depth.** Whatever ships must never sharpen along `k`",
    124: "**Do not build iterative deconvolution.** One regularised inverse filter buys within 0.19 dB of Richardson–Lucy at 1/237 the cost. This is the whole design of the opt-in plugin",
    125: "No prior may be shipped as a default on literature strength alone. TV measured *worse* than plain RL, and the authors state the ranking does not transfer between object types",
    126: "**The PSF accuracy budget is asymmetric**: in-focus precision matters, defocus width tolerates 30%. That is exactly the direction that makes self-calibration from the through-focus curve cheap enough to attempt",
    127: "**External corroboration of the selection-injects-energy thesis — measured in 2004 by the authors of the method it condemns.** ≈30% of pixels outside the range of every input frame is the defect strehl exists to remove",
    128: "**A structural argument for the normalised-weighted-sum merge strehl already ships, and against the `1/Σ\\|H\\|²` form the review proposed.** Range safety is free in one and absent in the other",
    129: "A fusion method's advantage can **invert sign** between synthetic and real content. Never accept a transform-domain win measured on synthetic textures — which is how most of them are measured",
    130: "**The depth-discontinuity case is outside all three forward models, stated by their own authors.** The occlusion work is genuinely open ground — subject to fact 411",
    131: "**Withdraw this claim before making it.** The halo has 28 years of prior art, including a paper predicting the exact non-monotonic transition fact 150 measured. The defensible claim is narrower and must be stated that way in any write-up",
    132: "A cheap published remedy for fact 150's bimodality already exists. **Try the focus-axis analogue of Wang 2015 before anything bespoke** — it is a strictly smaller change than the two-layer unmixing the review proposed",
    133: "Two causes, two fixes, only one intrinsic. **Zero-padding or apodisation is mandatory, not optional**, and a ringing report that does not say which cause it saw is uninterpretable",
    134: "Any self-calibrated OTF needs an **explicit normalisation to break the scale degeneracy**, or the estimate is unidentifiable. Both reference implementations pin it the same way",
    135: "**Design rule: exclude the zero-blur explanation from the search space.** MAP over image and kernel otherwise selects it, and the failure is silent",
    136: "A calibrated physical simulator with **withheld** ground truth already exists. Constrains M25's design — learn the spec, and do not read the GPL code",
    137: "**FRC cannot be fooled upward by noise amplification**, which is precisely how a deconvolution metric fails. This is the ground-truth-free instrument strehl needs to score any sharpening honestly",
    138: "All four reference implementations are GPL-3.0. **Papers readable, code untouchable.** The licence hygiene rule holds with no exception available",
    139: "After 30+ years in a field with harder physics, **both select and reconstruct still ship**. Evidence for strehl's plugin stance over picking a winner in the core",
}


def main():
    rows = {int(k): v for k, v in json.loads(SRC.read_text(encoding="utf-8")).items()}
    assert set(rows) == set(CONSEQUENCE), set(rows) ^ set(CONSEQUENCE)

    for n, (body, _) in rows.items():
        for ref in re.findall(r"[Ff]act (\d+)", body):
            assert not (120 <= int(ref) <= 139), f"row {n} references in-block fact {ref}"

    block = []
    for n in sorted(rows):
        body, label = rows[n]
        src = f"M19 §9 — {label}"
        block.append(f"| {n + SHIFT} | {body} | {CONSEQUENCE[n]} | {src} |")
    block[0] = block[0][:-1] + " *(proposed as fact 120; shifted +280, M20-V holds 122–139)* |"

    dst = DST.read_text(encoding="utf-8").split("\n")
    cur, last = "", None
    for k, l in enumerate(dst):
        if l.startswith("## "):
            cur = l
        if cur.startswith("## 4.") and re.match(r"\| \d+ \|", l):
            last = k
    assert last is not None
    DST.write_text("\n".join(dst[: last + 1] + block + dst[last + 1 :]), encoding="utf-8")
    print(f"added facts 400-419 (M19's 120-139, shifted +{SHIFT})")


main()
