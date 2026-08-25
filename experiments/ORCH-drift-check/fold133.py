"""Fold ORCH's first direct visual inspection of strehl's output.

Facts 1603-1608, disciplines 824-825.

Status label is OBSERVED for anything ORCH judged by eye. That is weaker than
MEASURED and stronger than ARGUED: a defect visible at 1:1 to a reader who did
not know what to look for is evidence, but it is not a number.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1602 |")
disc_line = full_line(raw, "823. ")

NEW_FACTS = [
    (
        1603,
        "OBSERVED",
        "ORCH",
        "**THE WORST ARTIFACT IN THE SHIPPED RENDER IS NOT THE HALO. IT IS A POLYGONAL "
        "PATCHWORK IN THE DEFOCUSED BACKGROUND.** On the first occasion in this project "
        "that ORCH viewed a rendered pixel, the out-of-focus white background of "
        "`bee-3` resolves at 1:1 into **irregular flat polygons with visible brightness "
        "steps between them** -- crazy paving. It is unmistakably non-photographic: a "
        "smoothly defocused background cannot contain hard-edged polygons. It covers a "
        "large fraction of the frame, and it is present **unchanged** in the shipped "
        "merge, in the F1 halo arm at d40, and in the F2 two-layer unmix "
        "(`C:\\dev\\strehl-out\\M87-before-after\\{00,01,04}-*-tight2x.png`). Every arm "
        "the project has built leaves the largest visible defect untouched.",
    ),
    (
        1604,
        "ARGUED",
        "ORCH",
        "**A MECHANISM FOR THE PATCHWORK, AND IT PREDICTS THAT THE CURE IS ALREADY "
        "WRITTEN AND SWITCHED OFF.** Where a region is defocused in *every* frame the "
        "through-focus response is flat, so the focus measure is noise-dominated and the "
        "argmax is near-random; the spatial regulariser then snaps that random field into "
        "**piecewise-constant regions**, which is what makes polygons; each polygon "
        "gathers from a different frame, and frames differ slightly in background "
        "brightness, which is what makes the **steps** between them visible. If this is "
        "right the fix is `STREHL_SOFT_GATE` (`merge.rs:483`, default **OFF**): where the "
        "election margin sits below the noise floor there is nothing to elect on and the "
        "correct estimator is a broad average, which is smooth *and* buys the sqrt(N) "
        "noise reduction. **Unverified.** M96 already computed the `margin-q8` and "
        "`confusion-radius` maps that would confirm or kill it.",
    ),
    (
        1605,
        "OBSERVED",
        "ORCH",
        "**M87'S AESTHETIC VERDICT ON THE HALO CORRECTION IS CONFIRMED BY AN INDEPENDENT "
        "EYE.** Comparing `09-BEE-BEFORE-shipped-merge.png` against "
        "`10-BEE-AFTER-F1-local-d40.png`, the after is **milky**: background structure "
        "present in the before is washed out and large regions go featureless. ORCH had "
        "already withdrawn the recommendation on M111's word (facts 1596-1601); this is "
        "the same conclusion reached from the images rather than from the reports, which "
        "makes the withdrawal safe against the possibility that M111 misread M87.",
    ),
    (
        1606,
        "OBSERVED",
        "ORCH",
        "**F2, THE TWO-LAYER UNMIX, IS VISUALLY A NO-OP.** "
        "`04-AFTER-F2-two-layer-unmix-tight2x.png` is indistinguishable by eye from "
        "`00-BEFORE-shipped-merge-tight2x.png` at the same framing. F2 is the "
        "physically-motivated arm -- the one that models the occluding edge as a "
        "two-layer composite and subtracts the foreground's defocused contribution. "
        "**So the project currently has no halo fix at all**: F1 works and looks worse, "
        "F2 does not change the image. This is an open problem, not a solved one.",
    ),
    (
        1607,
        "OBSERVED",
        "ORCH",
        "**AND THE HALO ITSELF IS REAL AND SEVERE, WHICH THE WITHDRAWAL MUST NOT BE READ "
        "AS DENYING.** On `crop-leg-halo.png` -- an **unstretched** view, not a "
        "contrast-boosted diagnostic -- a bright scalloped band traces the entire "
        "silhouette of the leg and both claws, and reads as a **cut-out sticker**. "
        "Withdrawing the F1 correction (facts 1596-1601) settles that *that cure* is "
        "worse than the disease; it settles nothing about the disease. Ranked by eye the "
        "defects are: **(1) background patchwork, (2) silhouette halo, (3) lateral "
        "chromatic aberration, (4) general softness.**",
    ),
    (
        1608,
        "OBSERVED",
        "ORCH",
        "**LATERAL CHROMATIC ABERRATION IS CONFIRMED PRESENT BY EYE, INDEPENDENTLY OF THE "
        "REPORTS THAT MEASURED IT.** `ORCH-look/crop-head-eye.png` at 1:1 shows clear "
        "purple and cyan fringing along the antenna edges against the lighter background. "
        "This corroborates the *diagnosis* of M107/M110/M113. It corroborates **nothing "
        "about the correction**, which remains un-adjudicated pending an audit of whether "
        "its 61.0 %/58.7 % figures come from the shipped pipeline and whether it was ever "
        "raced against a negative-strength arm rather than against OFF.",
    ),
]

NEW_DISCS = [
    (
        824,
        "**Look at the output.** This project ran 119 milestones, wrote 156 research "
        "reports and recorded 1602 facts before its orchestrator viewed a single "
        "rendered pixel, and ten minutes of looking **reordered the defect priority "
        "list** (facts 1603, 1607). The largest visible defect had no milestone, no "
        "fact and no name in the corpus, because every instrument the project built was "
        "pointed at a defect somebody had already thought of. **A metric can only "
        "answer the question it encodes; an image answers questions nobody asked.** "
        "Looking is not a substitute for measurement -- fact 1603 is labelled OBSERVED "
        "for that reason -- but it is how you find out which measurement is worth making.",
    ),
    (
        825,
        "**Withdrawing a cure is not withdrawing the diagnosis, and the corpus must say "
        "which one it means.** ORCH withdrew the halo correction on strong evidence "
        "(facts 1596-1601) and the next reader could reasonably have concluded the halo "
        "was not a real problem. It is a severe one (fact 1607), and the project now has "
        "**no** fix for it (fact 1606). **A negative result about a treatment is "
        "silent about the disease**, and in a corpus where facts are read out of order "
        "by agents who were not there, the two have to be stated as separate rows or the "
        "refutation will be mistaken for a dismissal.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

for block in (fact_block, disc_block):
    for line in block.split("\n"):
        stripped = _re.sub(r"`[^`]*`", "", line)
        assert stripped.count("**") % 2 == 0, "odd ** in: %s" % line[:90]
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert out != raw, "fact insertion did not land"
prev = out
out = out.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert out != prev, "discipline insertion did not land"

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
