"""Fold ORCH's radius stratification of the visible CA, and the by-eye baseline.

Facts 1499-1501, discipline 767. Measured by ORCH directly from M110's rendered
crops and the shipped profile constants; the normalisation convention was verified
against optics.rs rather than assumed, because using the wrong one would have made
every number describe a different quantity.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1498 |")
disc_line = full_line(raw, "766. ")

NEW_FACTS = [
    (
        1499,
        "MEASURED",
        "ORCH",
        "**The lateral CA that is visible by eye sits OUTSIDE the fitted support.** "
        "`bee-3-cpl` render is 7032 x 4688 (read from the TIFF header), half-diagonal "
        "4225.7 px. M110's crops in normalised field height: **hairs @(300,4200) r = "
        "0.8787**, **wing @(900,60) r = 0.8218** -- both **past** `support_r_max = 0.788` "
        "and therefore corrected by extrapolated model shape; specular @(900,2620) r = "
        "0.6225 and `wrapped-text-1` text @(4850,1750) r = 0.3456 are inside the fit. **The "
        "two crops where the fringing is conspicuous are the two outside the support; the "
        "one well inside it is a low-contrast region where CA is barely visible.** "
        "Normalisation was **verified, not assumed**: `optics.rs:138-139` defines "
        "`support_r_max` as normalised field height with 1.0 = half the sensel diagonal. "
        "`optics.rs:315-318` records the fit spanning r = 0.208-0.788, six of ten annuli "
        "populated, **outer two empty**, corner a **1.27x linear extrapolation**, declared "
        "but not enforced. ASSUMED (unverified): that M110's crop labels are output-pixel "
        "coordinates with top-left origin.",
    ),
    (
        1500,
        "MEASURED",
        "ORCH",
        "**Lateral CA confirmed dominant by a third independent by-eye read.** ORCH "
        "inspected M110's x5/x7 nearest-neighbour crops (`no resize/sharpen/tone change`) "
        "of `bee-3-cpl` without reading M110's or M107's verdicts first: every "
        "high-contrast edge carries a hard red/orange fringe on one side and cyan/teal on "
        "the other, **2-4 px wide**. The `default` and `lanczos3` arms show it "
        "**identically**, as they must -- neither has the correction on. The magenta "
        "highlight residual is **also visible**, as faint pink blotches in near-neutral "
        "bright areas of the specular crop, consistent with M109's measured 0.5060 % "
        "residual (fact 1495).",
    ),
    (
        1501,
        "ARGUED",
        "ORCH",
        "**Radius-dependent over-correction is the leading candidate explanation for "
        "M107's failed W3 bar.** W3 required >90 % of pixels to keep chroma sign and "
        "measured **75.1 %**, its own script printing `RECOLOURED, NOT REMOVED`. Lateral "
        "CA grows monotonically with field height and is zero at centre by construction "
        "(`optics.rs:141-142`), so an extrapolated radial coefficient that overshoots would "
        "**reverse fringe polarity** at high radius while behaving inside the fit -- which "
        "is exactly a sign flip. **Falsifiable and cheap:** stratify W3's sign-flip "
        "population at r = 0.788. If the flips concentrate at high radius the aggregate "
        "failure becomes a precise, fixable statement; if they are radius-uniform this "
        "explanation dies. Routed to M114. **Unmeasured.**",
    ),
]

NEW_DISCS = [
    (
        767,
        "**When a correction is radial and its fit has empty outer annuli, stratify every "
        "headline statistic at the support boundary before believing it.** A whole-frame "
        "aggregate silently mixes the fitted zone with the extrapolated one, and for a "
        "defect that grows monotonically with radius the **top decile is dominated by "
        "precisely the extrapolated pixels** -- so the most impressive number in the report "
        "is the one least supported by data. M107's -54.08 % top-decile improvement on "
        "`bee-3-cpl` is a materially weaker claim if produced mostly past r = 0.788 than "
        "the same number produced inside the fit, and the two cases are indistinguishable "
        "in the aggregate. Cost of the split: one mask (facts 1499, 1501).",
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
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "fold text contains 0x%02X" % o

raw2 = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert raw2 != raw, "fact insertion did not land"
raw3 = raw2.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert raw3 != raw2, "discipline insertion did not land"

for fid, _, _, _ in NEW_FACTS:
    assert raw3.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert raw3.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(raw3)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
