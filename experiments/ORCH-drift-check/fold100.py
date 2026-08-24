"""Fold M107's support answer, its instrument defect, and ORCH's by-eye kernel read."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1462,
     "**THE LATERAL-CA COEFFICIENT IS SUPPORTED TO r = 0.788 AND EXTRAPOLATED BEYOND IT, BUT 79 % OF THE "
     "CORNER CORRECTION IS STILL MEASURED.** Asked for its radial support profile rather than its "
     "goodness of fit, M107 registered bars S0-S5 in advance -- **including that it expected S2 to "
     "fail** -- and answered: fitted on `tweezers-cpl` (12 ROIs) plus `bee-3-cpl` (8), spanning "
     "**r = 0.208 to 0.788**, median 0.584, with **6 of 10 annuli populated** and **both outer annuli "
     "(0.80-0.90 and 0.90-1.00) empty**. Registered bar was `r_max >= 0.85`: **FAIL**. Because "
     "`d = eps·r` is linear, the corner displacement decomposes exactly: **2.98 sensels at r = 1.0, of "
     "which 2.35 is at or below a measured radius and 0.63 is the model's shape.** Shipped as "
     "`support_r_max: Option<f64> = Some(0.788)` on both profiles, **declared but not enforced** -- no "
     "clamp, on the stated ground that a behavioural change with no render behind it is unjustified.",
     "**This is the good version of the answer I was afraid of.** Six populated annuli across a 3.8x "
     "lever arm in `r` is real radial structure, and it is categorically unlike fact 1457's two-bin "
     "degeneracy -- **\"unsupported at the corner\" and \"unsupported everywhere\" are different "
     "findings and M107 correctly refused to let mine collapse into M109's.** The honest form of the "
     "result is a *declared valid radius*, which is strictly more informative than either a silent "
     "extrapolation or a refusal to ship. Two gaps remain and both are capture gaps, not method gaps: "
     "the outer field is empty on the subjects available, and **`eps_b` is `None` because every fitted "
     "ROI was red**, so the blue-green displacement is uncorrected by construction -- which matters, "
     "because the fringing visible in real crops has both warm and cool edges and only one of them is "
     "being addressed.",
     "M107-chroma, bars S0-S5 registered before the run; commit `a3d485a`"),
    (1463,
     "**A GEOMETRICALLY IMPOSSIBLE SUPPORT RADIUS PASSED UNDER THE VERDICT \"SUPPORT ADEQUATE\", AND "
     "THE VERDICT IS NOT WHAT CAUGHT IT.** M107's first support run normalised radii by the **half-"
     "resolution plane** diagonal instead of the **full-resolution sensel** diagonal, and reported "
     "`r_max = 1.575` -- a normalised field height above 1.0, which cannot exist. The instrument "
     "printed `SUPPORT ADEQUATE` alongside it. **It was caught by control S5, which had been written "
     "to check something else entirely**, failed for its own reasons, and sent its author back to "
     "output he had already read past. `eps_r` itself is unaffected -- `d` and `r` are both in sensels "
     "so the ratio is dimensionless -- and only the support statistic was wrong. **The same 2x error "
     "survives in a parent milestone's reporting line** (`e10_transfer.py` fixing plane dimensions at "
     "3516x2344), flagged and deliberately not touched.",
     "**A verdict cannot catch an impossible input, because a verdict is computed *from* the input.** "
     "The threshold was satisfied; the quantity was nonsense; those are compatible, and no amount of "
     "care in choosing the threshold would have helped. **The check that works is a physical-bounds "
     "assertion on the derived quantity itself** -- a normalised field height is in [0, 1] by "
     "construction, and that is cheaper to assert than any verdict is to design. S0 now does exactly "
     "that. Note the mechanism of the actual catch: **an unrelated control failing is one of the "
     "highest-yield events in this project**, because it is the only routine circumstance that makes "
     "an author re-read output they have already accepted.",
     "M107-chroma, self-reported defect; controls now two-sided (0.902 adequate / 0.394 starved)"),
    (1464,
     "**ORCH BY-EYE, ON THE FIRST 1:1 SHEETS: `lanczos3` IS VISIBLY SHARPER THAN THE SHIPPED DEFAULT ON "
     "TWO UNRELATED SUBJECTS, AND I SEE NO RINGING.** Read on M110's self-dating sheets at x5-x7 "
     "nearest-neighbour zoom with no resize, sharpen or tone change between arms. On `bee-3-cpl` hairs, "
     "individual hairs separate under `lanczos3` where the default merges them into a softer mass. On "
     "`wrapped-text-1`, a completely different subject, the fibrous texture and the light-dark boundary "
     "are both better resolved, **in the same direction**. A third crop, a `bee-3-cpl` specular, is "
     "**not a discriminator** -- the two arms are near-indistinguishable there and both are soft. "
     "**Chromatic fringing is loud in BOTH arms**, with warm and cool edges on bright specular "
     "boundaries.",
     "**ARGUED, and I am not an independent judge of this: I re-prioritised three agents on the "
     "strength of fact 1420 and I am now looking at its output hoping to see a win.** Recorded for "
     "what it is worth and explicitly subordinate to M113's independent read. Two things do follow "
     "with less bias attached. **The same-direction result on two unrelated subjects is weak evidence "
     "for fact 1461's untested stack-independence prediction**, and it is what a ringing artefact "
     "would *not* produce, since ringing scales with edge density and a bee's hairs and a text weave "
     "are not comparable in that respect. And **the fringing being equally loud in the shipped default "
     "directly corroborates fact 1452**: the kernel is not creating it, so removing the blur that "
     "hides it does not create it either.",
     "ORCH direct observation of `ZOOM-bee-3-cpl-hairs`, `ZOOM-wrapped-text-1-text`, "
     "`ZOOM-bee-3-cpl-specular` from M110's harness (`66ba510`)"),
]

DISCIPLINES = [
    (747,
     "**Assert physical bounds on a derived quantity; do not rely on the verdict computed from it.** A "
     "normalised field height above 1.0 passed under `SUPPORT ADEQUATE` (fact 1463), because a verdict "
     "is a function of its input and cannot detect that the input is impossible. **Every derived "
     "quantity with a known range -- a normalised radius in [0, 1], a correlation in [−1, 1], a "
     "fraction in [0, 1], an MTF in [0, 1] -- should be asserted against that range at the point of "
     "computation**, which costs one line and catches unit errors, resolution mismatches and axis "
     "confusions that no threshold can. Corollary, and it is the more valuable half: **when an "
     "unrelated control fails, re-read the output you already accepted.** That is the only routine "
     "event that makes an author revisit a result they have stopped questioning, and in this project it "
     "has now paid out repeatedly."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1461 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^746\. ", l))
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
    print("folded facts 1462-1464, discipline 747")


if __name__ == "__main__":
    main()
