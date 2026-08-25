"""M87 -- the wrap-up: the M121 cross-check, and three things made prominent.

The orchestrator re-scoped this milestone to WRAP UP AND WRITE THE NULL, with
one new measurement (the M121 cross-check, landed by 110-crosscheck.py) and
three presentation requirements:

  1. the M121 cross-check answer, with its controls;
  2. P146's self-correction lifted out of the fact table into the body;
  3. the --srgb pins retired rather than refreshed, and said to be so.

Plus one ARGUED paragraph on whether the waxy-blob plateau seam and the
occlusion rim share a root cause, flagged as a lead for whoever takes the gate
work, explicitly NOT re-deriving anyone else's measurement.

The 72.9% erasure failure was already in the body at four sites (the executive
summary, the adjudication, the ship section and the gallery table), so it is
cross-referenced rather than duplicated -- adding a fifth statement of it would
have tripped this milestone's own duplicate-site checks.

Same guards as P144-P147: control_s29 anchors, the 100.00% collision, CRLF.
"""
import os
import pathlib
import shutil
import sys

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"

FORBIDDEN = [
    "It measured **100.00%** and printed PASS.",
    "It measured **100.00%** and printed **PASS**.",
    "| **100.00%** | 0.4137 |",
]

MINUS = "\u2212"

ROWS = [
    (
        "| P148 | **The merge's residual veil is concentrated inside one "
        "focus-window radius, which merges this milestone's null with M121's "
        "rim result into a single mechanism.** Per-distance residual of the "
        "gate-0 merge against its own far reference, same cube, mask and "
        "distance field as step 70: mean depth **12.250%** over d in 2-13 "
        "against **5.506%** over d in 14-22, a concentration ratio of "
        "**2.225x** against a preregistered bar of 2.0x, decaying to "
        "**18.3%** of peak by d = 13 against a bar of 25%. Half-depth "
        "distance **7 px**, against M121's rim w50 of 10.00 px and cutoff of "
        "13.25 px, and `WINDOW_RADIUS = 13` at `focus.rs:83`. | **The "
        "controls are what make this mean anything, and they came out the "
        "other way.** C-SINGLE: the same statistic on the mean single-frame "
        "profile gives **1.482x**, and across all 299 frames individually the "
        "ratio is 1.514x +/- 0.193 with a **maximum of 1.962x** -- every "
        "single frame falls below the merge. C-RAND: the random per-pixel "
        "merge gives **1.472x**. Single-frame half-depth is **22 px** against "
        "the merge's 7 px. So the concentration is a property of the "
        "election, not of binning a band that is only 20 px wide. The two "
        "half-depth numbers are the same scale and are not the same "
        "statistic; I claim agreement in scale, not in value. | MEASURED |"
    ),
    (
        "| P149 | **My own 74.76% veil-removal headline is a band average "
        "over a profile that varies six-fold, and it flatters the merge "
        "exactly where the eye looks.** Removal fraction by distance, merge "
        "against the mean single frame: **34.6%** at d = 2, **82.3%** at "
        "d = 13, **59.5%** at d = 22. The residual itself runs from "
        "&#8722;24.97% at d = 2 to a minimum of &#8722;4.38% at d = 14 and "
        "then deepens again to &#8722;7.29% at d = 22. | **The pooled figure "
        "is correctly computed and misleadingly read, including by me.** At "
        "the boundary pixels a viewer actually resolves as the halo edge the "
        "election removes about a third of the veil, not three quarters. This "
        "strengthens the mechanism rather than weakening it -- the merge "
        "fails hardest precisely where the focus window's support straddles "
        "the occluding edge -- but the number I have been quoting to the "
        "orchestrator all night is a band average and I should have said so. "
        "The outer re-deepening beyond d = 17 is **not** explained by the "
        "window and I have no account of it. | MEASURED |"
    ),
    (
        "| P150 | **Sections 33 and 34 rest on `--srgb` renders and are "
        "therefore not measurement-grade, and the right response is to retire "
        "the pins rather than refresh them.** Four scripts read the pinned "
        "gate TIFFs -- `100-gate-veildepth.py:158`, `96-gate-final.py:73`, "
        "`97-gate-attrib.py:76`, `102-robust.py:84` -- and those pins were "
        "rendered `--srgb --demosaic`. Every gate-ladder magnitude in this "
        "report, **+2.3463 pp** and **0.0572 pp**, is an sRGB-space number. | "
        "**The conclusion those numbers carry survives; their magnitudes do "
        "not transfer.** A monotone per-channel transfer curve preserves sign "
        "and rank order, so a swing that came back at 11.86% of prediction "
        "with the sign reversed, and at 0.289% of prediction once the "
        "reference is pinned, cannot be turned into a confirmation by any "
        "gamma. What cannot be quoted in linear terms is the pp magnitude. "
        "Section 25's mechanism claim is untouched, because it reads "
        "`raw_image_visible` through `m87lib.py:139` and never sees a "
        "developed pixel. | MEASURED |"
    ),
    (
        "| P151 | **Hypothesis for whoever takes the gate work: the plateau "
        "seam and the occlusion rim are the same defect seen on two "
        "subjects.** A boolean admission gate must choose among frames whose "
        "through-focus response is genuinely bimodal at an occluding edge, "
        "because the veil is present in every frame and no observation "
        "contains clean background. On a flat plateau the same boolean choice "
        "elects one frame per region and renders a seam; at an edge it elects "
        "one layer and renders a rim. Both would be relieved by a soft or "
        "contrast-scaled admission rather than by any edge-specific fix. | "
        "**ARGUED, and deliberately not measured here.** The orchestrator "
        "asked for the lead without spending this milestone's remaining "
        "budget on it, and the supporting measurements belong to others: "
        "M121's finding that gate 0 and gate 4 are equivalent, and the "
        "separate diagnosis that the gate's admission tolerance is absolute "
        "while the focus response is contrast-scaled. I have re-derived "
        "neither. What M87 contributes is the edge half of the claim: "
        "removal happens at `n_eff = 1.000`, so averaging is not the "
        "mechanism on either subject. | ARGUED |"
    ),
]

ANCHOR = "Three limits, stated rather than buried."

PARA = """**The cross-check that turns two nulls into one mechanism.** This
milestone and M121 reached the same conclusion from opposite directions --
M121 by measuring that the residual rim carries the focus window's length
scale, M87 by measuring that veil removal happens at `n_eff = 1.000` and so
cannot be driven by averaging. Two statistics on different fields agreeing is
worth more than either alone, but only if they are describing the same pixels.
So: is M87's residual concentrated inside the 0-13 px band where M121's rim
lives, or spread across M87's full 2-22 px window?

**Concentrated.** Mean residual depth is **12.250%** over d in 2-13 against
**5.506%** over d in 14-22 -- a ratio of **2.225x** against a bar of 2.0x
registered before the numbers existed -- and the residual has fallen to
**18.3%** of its peak by d = 13, against a registered bar of 25%.

**The controls decide whether that sentence means anything, and they were
built to be able to fail.** A concentration statistic on a band only 20 px
wide could report "concentrated" for any profile rising toward a far
asymptote, purely as an artefact of binning. The single frames carry the full
veil, driven by the defocus blur radius rather than by the focus window, so
the same statistic run on them must come out the *other* way -- and it does:

| field | inner d 2-13 | outer d 14-22 | ratio | half-depth |
|---|---|---|---|---|
| gate-0 merge | **12.250%** | **5.506%** | **2.225x** | **7 px** |
| mean single frame (C-SINGLE) | 31.303% | 21.125% | 1.482x | 22 px |
| random per-pixel merge (C-RAND) | 31.041% | 21.094% | 1.472x | -- |

Across all 299 frames taken individually the ratio is 1.514x +/- 0.193 with a
maximum of **1.962x**, so **every single frame falls below the merge's
2.225x** rather than merely the average doing so. The merge's half-depth of
7 px against the single frames' 22 px is a three-fold dissociation on the same
pixels with the same code.

**The joint statement, then, is a mechanism rather than a pair of nulls:** the
merge removes the veil everywhere except within roughly one focus-window
radius of the occluding edge, because that is exactly where the window's
support straddles the boundary and the election has no frame that is
unambiguously right. M121's rim w50 of 10.00 px, its cutoff of 13.25 px, and
`WINDOW_RADIUS = 13` at `focus.rs:83` sit on one side; M87's half-depth of
7 px sits on the other. **These are the same scale, computed independently,
and they are not the same number** -- I claim agreement in scale, which is
what two different statistics on two different fields can support, and not
agreement in value, which they cannot.

**A correction against my own headline, found while answering that question.**
The 74.76% veil-removal figure I have quoted all night is a band average, and
the profile it averages varies six-fold. Removal by distance is **34.6%** at
d = 2, **82.3%** at d = 13 and **59.5%** at d = 22. At the boundary pixels a
viewer actually resolves as the halo edge, the election removes about a third
of the veil, not three quarters. The figure is correctly computed and I have
been reading it too kindly; the mechanism survives and is in fact sharpened by
the correction, since the failure is deepest exactly where the window
straddles the edge. One feature I cannot account for: beyond d = 17 the
residual stops shrinking and deepens again, to &#8722;7.29% at d = 22. The
focus window does not predict that and I am not going to invent a reason for
it.

**On the rank statistic, restated here because it belongs in the body and not
in a footnote.** This report quoted a Spearman rho of &#8722;1.0000 for the
gate ladder against veil depth. A coefficient printed to four decimals invites
the reading that it is strong evidence. It is not: with four rungs there are
only 24 permutations, so a perfect reversal arises by chance with probability
**0.0417**, and a perfect coefficient of either sign with probability 0.0833.
It does not clear p < 0.01 until n = 5. **A coefficient's number of digits is
not its number of observations.** The gate-ladder conclusion is kept because
it rests on magnitudes measured over 451,008 pixels -- a swing at 11.86% of
prediction with the sign reversed, collapsing to 0.289% once the reference is
pinned -- and not on the rank at all. Had the argument rested on the rho, this
paragraph would be a retraction instead of a caveat.

**Why the `--srgb` pins are being retired rather than re-rendered.** The
gate-ladder operands were produced with `--srgb --demosaic`, and a developed
space is not a measurement space: the output matrix mixes channels and the
demosaic assumes cross-channel smoothness, neither of which a metric should be
asked to see through. Every gate-ladder magnitude in this report is therefore
an sRGB-space number, and refreshing the pins after the colour path changed
would produce a fresh set of numbers with the same defect. **The correct
action is to stop quoting the magnitudes, not to regenerate them.** The sign
and the ordering survive, which is all the refutation needed. Section 25 is
unaffected for a structural reason rather than a lucky one: it reads
`raw_image_visible` through `m87lib.py:139` and has never seen a developed
pixel.

**One lead, ARGUED, handed on rather than pursued.** A boolean admission gate
at an occluding edge is forced to choose among frames whose through-focus
response is genuinely bimodal, since the veil is in every frame and no
observation anywhere in the stack contains clean background. The same boolean
choice on a flat plateau elects a single frame per region and renders a seam.
If that is right, the waxy-blob plateau artefact and the occlusion rim are one
defect on two subjects, and both would be relieved by a soft or
contrast-scaled admission rather than by anything edge-specific. M87
contributes only the edge half of that claim and has deliberately not
re-derived the plateau measurements, which belong to other milestones."""


def main():
    raw = DOC.read_bytes().decode()
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"

    if "| P148 |" in raw:
        print("wrap-up already present -- nothing to do")
        return

    for row in ROWS:
        bare = row.replace("\\|", "")
        assert bare.count("|") == 5, "fact row needs exactly 5 unescaped pipes"
        assert row.count("`") % 2 == 0, "fact row backtick count is odd"
        assert MINUS not in row, "fact rows use the &#8722; entity, not U+2212"
    assert PARA.count("`") % 2 == 0, "paragraph backtick count is odd"
    assert MINUS not in PARA, "paragraph uses the &#8722; entity, not U+2212"
    for f in FORBIDDEN:
        for t in ROWS + [PARA]:
            if f in t:
                sys.exit("NEW PROSE REPRODUCES A control_s29 ANCHOR: %r" % f)
    for t in ROWS + [PARA]:
        if "100.00%" in t:
            sys.exit("NEW PROSE QUOTES 100.00%% -- the exact P143 collision")

    backup = pathlib.Path(os.environ["TEMP"]) / "M87-occlusion.before-wrapup.md"
    shutil.copy2(DOC, backup)
    print("backed up to %s" % backup)

    if raw.count(ANCHOR) != 1:
        sys.exit("PARA ANCHOR NOT FOUND EXACTLY ONCE (%d)" % raw.count(ANCHOR))
    body = "\r\n".join(PARA.split("\n"))
    raw = raw.replace(ANCHOR, body + "\r\n\r\n" + ANCHOR, 1)

    lines = raw.split("\r\n")
    idx = [n for n, l in enumerate(lines) if l.startswith("| P147 |")]
    if len(idx) != 1:
        sys.exit("expected exactly one P147 row, found %d" % len(idx))
    for k, row in enumerate(ROWS):
        lines.insert(idx[0] + 1 + k, row)
    raw = "\r\n".join(lines)

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode())

    after = DOC.read_bytes().decode()
    for f in FORBIDDEN:
        if after.count(f) != 1:
            sys.exit("POST-WRITE: control_s29 anchor %r moved" % f)
    for tag in ("| P148 |", "| P149 |", "| P150 |", "| P151 |"):
        if tag not in after:
            sys.exit("POST-WRITE CHECK FAILED: %s missing" % tag)
    print("added P148-P151 and the wrap-up section; %d lines"
          % (after.count("\n") + 1))


if __name__ == "__main__":
    main()
